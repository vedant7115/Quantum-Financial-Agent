import React from "react";
import { Lock } from "lucide-react";
import "../styles/quantum-next.css";

/** Placeholder shown in the report where a section is not part of the user's plan.
 *  The content itself is withheld by the server, not hidden in the browser. */
export default function LockedSection({ id, title, description, onUpgrade }) {
  return (
    <section id={id} data-section className="qx qx-lock">
      <div className="qx-lock-icon" aria-hidden="true">
        <Lock size={18} />
      </div>
      <div className="qx-lock-text">
        <h3 className="qx-h3">{title}</h3>
        <p className="qx-body">{description}</p>
      </div>
      <button type="button" className="qx-btn qx-btn-primary qx-btn-inline" onClick={onUpgrade}>
        See plans
      </button>
    </section>
  );
}
