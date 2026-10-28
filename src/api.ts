export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function fetchMeta() {
  const res = await fetch(`${API_URL}/meta`);
  if (!res.ok) throw new Error('Failed to fetch metadata');
  return res.json();
}

export async function fetchModelPerformance() {
  const res = await fetch(`${API_URL}/model-performance`);
  if (!res.ok) throw new Error('Failed to fetch model performance');
  return res.json();
}

export async function generateForecast(params: {
  start_date: string;
  days: number;
  resolution: 'hourly' | 'daily';
  temp_change: number;
}) {
  const res = await fetch(`${API_URL}/forecast`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Error generating forecast: ${res.status}`);
  }
  return res.json();
}
