'use client';

import { useState, useEffect } from 'react';

export default function Home() {
  const [health, setHealth] = useState<object | null>(null);
  const [version, setVersion] = useState<object | null>(null);

  useEffect(() => {
    // Fetch health
    // Note: In production/docker, this might need an environment variable, 
    // but for local 'make start', localhost:8000 is correct.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error('Health fetch error:', err));

    // Fetch version
    fetch(`${apiUrl}/version`)
      .then(res => res.json())
      .then(data => setVersion(data))
      .catch(err => console.error('Version fetch error:', err));
  }, []);

  const roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support'];

  return (
    <main className="flex min-h-screen flex-col items-center p-8 bg-zinc-900 text-white">
      <h1 className="text-4xl font-bold mb-8">LoL Coach Draft</h1>

      <div className="mb-8 p-4 border border-zinc-700 rounded bg-zinc-800 w-full max-w-2xl">
        <h2 className="text-xl font-bold mb-2">Backend Status</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="font-semibold text-zinc-400">Health:</span>
            <pre className="mt-1 p-2 bg-black rounded text-green-400 text-xs">
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>
          <div>
            <span className="font-semibold text-zinc-400">Version:</span>
            <pre className="mt-1 p-2 bg-black rounded text-blue-400 text-xs">
              {JSON.stringify(version, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      <div className="w-full max-w-6xl grid grid-cols-2 gap-12">
        {/* Blue Side */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-blue-400 text-center">Blue Team (Ally)</h2>
          {roles.map((role) => (
            <div key={`blue-${role}`} className="flex items-center p-4 bg-zinc-800 rounded border-l-4 border-blue-500">
              <div className="w-16 font-bold">{role}</div>
              <div className="flex-1 text-center text-zinc-500">Pick Slot</div>
            </div>
          ))}
        </div>

        {/* Red Side */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-red-400 text-center">Red Team (Enemy)</h2>
          {roles.map((role) => (
            <div key={`red-${role}`} className="flex items-center p-4 bg-zinc-800 rounded border-r-4 border-red-500 flex-row-reverse text-right">
              <div className="w-16 font-bold">{role}</div>
              <div className="flex-1 text-center text-zinc-500">Pick Slot</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
