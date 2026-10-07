/**
 * StepDots — visual indicator for the 3-step rule.
 * Every user action in Sanskriti is ≤ 3 steps; this shows where you are.
 */
export default function StepDots({ step, total = 3 }) {
  const steps = Array.from({ length: total }, (_, i) => i + 1);
  return (
    <div className="step-dots justify-center" aria-label={`Step ${step} of ${total}`}>
      {steps.map((s) => (
        <span
          key={s}
          className={`step-dot ${
            s < step ? "done" : s === step ? "active" : ""
          }`}
          aria-current={s === step ? "step" : undefined}
        />
      ))}
    </div>
  );
}
