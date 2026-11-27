import React from 'react';

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message || 'UI Error' };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#F0F2F5] p-6 flex items-center justify-center">
          <div className="bg-white border border-gray-300 rounded-xl p-5 max-w-md w-full">
            <h2 className="text-lg font-bold text-[#1C1E21]">App Recovery</h2>
            <p className="text-sm text-gray-600 mt-2">{this.state.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 w-full bg-[#1877F2] text-white font-semibold py-2.5 rounded-lg"
            >
              Reload App
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
