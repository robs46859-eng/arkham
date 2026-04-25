import React from 'react';
import { Link } from 'react-router-dom';

type LegalVariant =
  | 'privacy'
  | 'terms'
  | 'indemnification'
  | 'refund'
  | 'billing'
  | 'billing-success'
  | 'billing-cancel';

interface LegalPageProps {
  variant: LegalVariant;
}

function renderBody(variant: LegalVariant) {
  switch (variant) {
    case 'privacy':
      return (
        <>
          <section className="legal-section">
            <h2>Information We Collect</h2>
            <p>
              We collect account details, tenant identifiers, project inputs, uploaded files,
              billing metadata, and workflow events required to provide the platform. We do not
              treat your project data as open training material for unrelated customers.
            </p>
          </section>
          <section className="legal-section">
            <h2>How We Use It</h2>
            <p>
              We use your information to authenticate users, process project workflows, generate
              deliverables, support billing, detect abuse, and maintain platform security. We may
              retain operational logs, audit records, and safety telemetry as needed to run the
              service responsibly.
            </p>
          </section>
          <section className="legal-section">
            <h2>Sharing and Security</h2>
            <p>
              We share data only with infrastructure, payment, and model providers that are needed
              to operate the service. Access is restricted by tenant scope, role, and operational
              need. If you need a data processing addendum or deletion request, contact support.
            </p>
          </section>
        </>
      );
    case 'terms':
      return (
        <>
          <section className="legal-section">
            <h2>Use of Service</h2>
            <p>
              You may use the platform only for lawful business purposes and only for data you are
              authorized to submit. You remain responsible for reviewing outputs before relying on
              them for procurement, construction, compliance, or contractual decisions.
            </p>
          </section>
          <section className="legal-section">
            <h2>Output and Responsibility</h2>
            <p>
              The platform provides structured automation and AI-assisted deliverables, not licensed
              professional advice. You are responsible for final validation, approval, and any
              downstream use of generated estimates, specifications, proposals, or reports.
            </p>
          </section>
          <section className="legal-section" id="indemnification">
            <h2>Indemnification</h2>
            <p>
              You agree to defend, indemnify, and hold harmless the service operator, affiliates,
              officers, employees, and contractors from claims, damages, liabilities, losses, and
              expenses arising out of your misuse of the platform, your submitted content, your
              violation of law, or your breach of these terms.
            </p>
          </section>
          <section className="legal-section">
            <h2>Limitations</h2>
            <p>
              The service is provided on an as-available basis. To the maximum extent permitted by
              law, liability is limited to fees actually paid for the service during the period
              giving rise to the claim.
            </p>
          </section>
        </>
      );
    case 'indemnification':
      return (
        <>
          <section className="legal-section">
            <h2>Indemnification</h2>
            <p>
              You agree to defend, indemnify, and hold harmless the service operator, affiliates,
              officers, employees, and contractors from claims, damages, liabilities, losses, and
              expenses arising out of your misuse of the platform, your submitted content, your
              violation of law, or your breach of these terms.
            </p>
          </section>
          <section className="legal-section">
            <h2>Scope</h2>
            <p>
              This obligation applies to third-party claims tied to your data, downstream use of
              platform output, unlawful conduct, or representations you make to customers,
              subcontractors, regulators, or counterparties using platform-generated materials.
            </p>
          </section>
        </>
      );
    case 'refund':
      return (
        <>
          <section className="legal-section">
            <h2>Subscriptions</h2>
            <p>
              Paid plans renew automatically until canceled. You can manage or cancel the
              subscription through the customer billing portal once an account has completed
              checkout.
            </p>
          </section>
          <section className="legal-section">
            <h2>Refunds</h2>
            <p>
              Fees already charged are generally non-refundable except where required by law or
              where we explicitly approve a service-credit or refund adjustment. If you believe a
              charge was made in error, contact billing support within 14 days of the charge date.
            </p>
          </section>
          <section className="legal-section">
            <h2>Cancellations</h2>
            <p>
              Cancellation stops future renewals but does not retroactively void charges for the
              current billing period. Access and plan entitlements may continue through the end of
              the paid term unless otherwise stated.
            </p>
          </section>
        </>
      );
    case 'billing':
      return (
        <>
          <section className="legal-section">
            <h2>Billing Access</h2>
            <p>
              Billing is tied to the authenticated tenant account. Checkout creates a hosted Stripe
              session. Returning customers use the billing portal to update cards, invoices,
              subscriptions, and cancellation settings.
            </p>
          </section>
          <section className="legal-section">
            <h2>Before Launch</h2>
            <p>
              This page should be the return destination for Stripe customer portal sessions. Keep
              this route live before activating production billing so support, cancellation, and
              policy links resolve cleanly from Stripe.
            </p>
          </section>
        </>
      );
    case 'billing-success':
      return (
        <section className="legal-section">
          <h2>Checkout Complete</h2>
          <p>
            Stripe has returned control to the app. If the subscription webhook has processed
            successfully, tenant billing status should update shortly. You can return to the app or
            contact support if the plan does not reflect within a few minutes.
          </p>
        </section>
      );
    case 'billing-cancel':
      return (
        <section className="legal-section">
          <h2>Checkout Canceled</h2>
          <p>
            No subscription was activated. You can return to billing and start checkout again when
            ready. If you were sent here unexpectedly, confirm the correct account and payment flow
            before retrying.
          </p>
        </section>
      );
  }
}

const PAGE_COPY: Record<LegalVariant, { eyebrow: string; title: string; summary: string }> = {
  privacy: {
    eyebrow: 'Privacy Policy',
    title: 'Data Use And Handling',
    summary:
      'How account, project, workflow, and billing information is processed for platform operations.',
  },
  terms: {
    eyebrow: 'Terms Of Service',
    title: 'Platform Terms',
    summary:
      'Service rules, responsibility boundaries, indemnification, and baseline commercial terms.',
  },
  refund: {
    eyebrow: 'Refund Policy',
    title: 'Refunds And Cancellations',
    summary:
      'How recurring charges, cancellations, and refund requests are handled for paid plans.',
  },
  billing: {
    eyebrow: 'Billing',
    title: 'Customer Billing',
    summary:
      'Account billing entry point for subscription management, payment updates, and support routing.',
  },
  indemnification: {
    eyebrow: 'Indemnification',
    title: 'Defense And Hold Harmless',
    summary:
      'Third-party claim allocation for misuse, submitted data, and downstream reliance on platform output.',
  },
  'billing-success': {
    eyebrow: 'Billing',
    title: 'Payment Success',
    summary: 'Stripe checkout completed and returned to the app.',
  },
  'billing-cancel': {
    eyebrow: 'Billing',
    title: 'Payment Canceled',
    summary: 'Stripe checkout was canceled before subscription activation.',
  },
};

export default function LegalPage({ variant }: LegalPageProps) {
  const copy = PAGE_COPY[variant];

  return (
    <div className="legal-shell">
      <header className="legal-hero">
        <div className="legal-grid" />
        <Link className="legal-back" to="/">
          Back To Site
        </Link>
        <div className="legal-eyebrow">{copy.eyebrow}</div>
        <h1 className="legal-title">{copy.title}</h1>
        <p className="legal-summary">{copy.summary}</p>
      </header>

      <main className="legal-body">
        {renderBody(variant)}

        <section className="legal-section legal-contact">
          <h2>Contact</h2>
          <p>
            For privacy, legal, refund, or billing issues, publish your real support address and
            phone before launch. This route should be updated with production contact details and
            any state-specific consumer disclosures you need.
          </p>
        </section>
      </main>
    </div>
  );
}
