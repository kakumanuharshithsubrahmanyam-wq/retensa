export default function AIPlan({ llm }) {
  if (!llm) return null;
  const plan = llm.retention_plan || {};
  const fallback = llm.recommendation_source === "deterministic" || llm.llm_status !== "ok";
  return (
    <div className="card explain-card">
      <div className="card-title" style={{ marginBottom: 8 }}>AI Retention Plan</div>
      {fallback && (
        <div className="card-sub" style={{ marginBottom: 10 }}>
          AI-generated narrative unavailable. Showing deterministic retention plan.
        </div>
      )}
      <p>{plan.summary}</p>
      {plan.why_at_risk?.length > 0 && (
        <ul>
          {plan.why_at_risk.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
      <p><b>{plan.recommended_action}</b></p>
      <p>{plan.action_reason}</p>
      <p>{plan.scenario_context}</p>
      <div className="explain-footer">{plan.caution}</div>
    </div>
  );
}
