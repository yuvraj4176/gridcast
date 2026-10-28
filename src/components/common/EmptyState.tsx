interface EmptyStateProps {
  onGenerate: () => void;
}

export function EmptyState({ onGenerate }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-art">
        <span>⌁</span>
        <i />
        <b />
      </div>
      <p className="eyebrow">READY WHEN YOU ARE</p>
      <h1>Map the next demand curve.</h1>
      <p>Choose a date and period, then click Generate Forecast.</p>
      <button className="secondary" onClick={onGenerate}>
        Generate a sample forecast →
      </button>
    </section>
  );
}
