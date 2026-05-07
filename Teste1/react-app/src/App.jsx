import React, { useState } from 'react'
import VanillaOrb from './components/VanillaOrb.jsx'

function App() {
  const [isListening, setIsListening] = useState(false)

  return (
    <>
      <h1>🔮 Teste 1 — Three.js Wireframe Orb (React)</h1>
      <div className="orb-wrapper">
        <VanillaOrb isListening={isListening} />
      </div>
      <div className="controls">
        <button
          className={isListening ? 'active-btn' : ''}
          onClick={() => setIsListening(!isListening)}
        >
          {isListening ? '⏸ Stop Listening' : '▶ Start Listening'}
        </button>
      </div>
    </>
  )
}

export default App
