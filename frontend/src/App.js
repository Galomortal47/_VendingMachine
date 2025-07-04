// frontend/src/App.js
import { useState } from "react";

function App() {
  const [text, setText] = useState("");
  const [user, setUser] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: text,
    });
    const data = await res.json();
    setUser(data);
  }

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Alice is 29 years old"
        />
        <button type="submit">Extract</button>
      </form>

      {user && (
        <div>
          <h2>Parsed result</h2>
          <pre>{JSON.stringify(user, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
