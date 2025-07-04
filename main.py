import os
import openai
import sqlalchemy
from fastapi import FastAPI, Body, HTTPException
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    select,
)
import databases

# ── Configuration ──────────────────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# ── Database setup ─────────────────────────────────────────────────────────
database = databases.Database(DATABASE_URL)
metadata = MetaData()

# Logs all requests/responses
logs_table = Table(
    "logs", metadata,
    Column("id",      Integer, primary_key=True),
    Column("message", String,  nullable=False),
)

# Single test user
users_table = Table(
    "users", metadata,
    Column("id",    Integer, primary_key=True),
    Column("name",  String,  unique=True, nullable=False),
    Column("money", Integer,            nullable=False),
)

# Available drinks
drinks_table = Table(
    "drinks", metadata,
    Column("id",    Integer, primary_key=True),
    Column("name",  String,  unique=True, nullable=False),
    Column("cost",  Integer,            nullable=False),
    Column("stock", Integer,            nullable=False),
)

# A sync-only engine for CREATE / SELECT (avoids the SQLite 4-tuple bug)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Ensure tables exist immediately on import
metadata.create_all(engine)

# ── App & Lifespan ──────────────────────────────────────────────────────────
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await database.connect()

    # seed via the sync engine so we never call fetch_one/fetch_val
    with engine.begin() as conn:
        # seed drinks if empty
        if not conn.execute(select(drinks_table.c.id).limit(1)).first():
            conn.execute(drinks_table.insert(), [
                {"name": "soda",        "cost": 5,  "stock": 30},
                {"name": "orangejuice", "cost": 10, "stock": 5},
                {"name": "water",       "cost": 2,  "stock": 10},
            ])
        # seed user if empty
        if not conn.execute(select(users_table.c.id).limit(1)).first():
            conn.execute(users_table.insert().values(name="john", money=20))


@app.on_event("shutdown")
async def on_shutdown():
    await database.disconnect()


# ── Purchase Endpoint ──────────────────────────────────────────────────────
@app.post("/extract")
async def extract_raw(text: str = Body(..., media_type="text/plain")):
    """
    1) Ask GPT which drink the user wants.
    2) Verify price vs. john's balance.
    3) Deduct cost, log everything, return a one-word response.
    """
    # 1) Determine desired product via LLM
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "Answer with exactly one word: soda, orangejuice, water or none."},
            {"role": "user", "content": text},
        ],
    )
    product = response.choices[0].message.content.strip().lower()
    if product not in {"soda", "orangejuice", "water"}:
        raise HTTPException(400, f"Invalid product: {product}")

    # 2) Query cost & balance (sync SELECTs via engine)
    with engine.connect() as conn:
        cost_row    = conn.execute(
            select(drinks_table.c.cost).where(drinks_table.c.name == product)
        ).first()
        money_row   = conn.execute(
            select(users_table.c.money).where(users_table.c.name == "john")
        ).first()

    if not cost_row or not money_row:
        raise HTTPException(404, "Product or user not found")

    cost, balance = cost_row[0], money_row[0]
    if balance < cost:
        # log and refuse
        await database.execute(logs_table.insert().values(
            message=f"Rejected {product}: balance {balance} < cost {cost}"
        ))
        return {"status": "insufficient_funds"}

    # 3) Deduct & log
    new_balance = balance - cost
    await database.execute(
        users_table.update()
            .where(users_table.c.name == "john")
            .values(money=new_balance)
    )

    await database.execute(logs_table.insert().values(
        message=f"Request: {text}"
    ))
    reply = product  # one-word reply per your original requirement
    await database.execute(logs_table.insert().values(
        message=f"Response: {reply}"
    ))

    return {"status": "success", "product": reply}
