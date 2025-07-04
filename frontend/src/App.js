// src/App.js
import { useState } from "react";
import styles from "./App.module.css";  // CSS Module import

function App() {
  const [text, setText] = useState("");
  const [user, setUser] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: text.trim(),
    });
    setUser(await res.json());
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Vending Machine NLP</h1>

      <form onSubmit={handleSubmit} className={styles.form}>
        <textarea
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Alice is 29 years old"
        />
        <button type="submit" className={styles.button}>
          Extract
        </button>
      </form>

      {user && (
        <div className={styles.resultCard}>
          <div className={styles.resultHeader}>Parsed Result</div>
          <pre className={styles.pre}>
            {JSON.stringify(user, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;
