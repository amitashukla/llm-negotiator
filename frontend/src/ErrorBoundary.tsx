import React from "react";

type Props = { children: React.ReactNode };

type State = { hasError: boolean; message: string };

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message || String(err) };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, fontFamily: "system-ui", color: "#1f2937" }}>
          <h2 style={{ fontSize: 18, margin: "0 0 8px" }}>Something went wrong</h2>
          <p style={{ margin: 0, fontSize: 14, color: "#6b7280" }}>{this.state.message}</p>
          <button
            type="button"
            style={{ marginTop: 16 }}
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
