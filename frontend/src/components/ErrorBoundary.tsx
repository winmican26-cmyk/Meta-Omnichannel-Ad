import { Component, type ReactNode, type ErrorInfo } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
            <AlertTriangle size={32} className="text-red-400" />
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-text-muted max-w-md mb-6">
            An unexpected error occurred while rendering this page.
          </p>
          {this.state.error && (
            <pre className="text-xs text-red-400/70 bg-surface-hover rounded-lg p-3 max-w-lg overflow-auto mb-6 text-left">
              {this.state.error.message}
            </pre>
          )}
          <Button variant="default" onClick={this.handleRetry} className="gap-2">
            <RefreshCw size={16} />
            Try Again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
