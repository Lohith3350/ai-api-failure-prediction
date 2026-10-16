import React from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

function App() {
  return (
    <main className="container">
      <p className="eyebrow">REAL-TIME AI FOR CRITICAL DECISIONS</p>
      <h1>API Failure Prediction</h1>
      <p className="sub">Starter dashboard — connect the telemetry and prediction APIs as modules are integrated.</p>
      <section className="grid">
        <article><span>Services monitored</span><strong>—</strong></article>
        <article><span>Warnings</span><strong>—</strong></article>
        <article><span>Critical services</span><strong>—</strong></article>
      </section>
      <section className="panel">
        <h2>Incident feed</h2>
        <p>No incidents connected yet. Backend integration is pending.</p>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
