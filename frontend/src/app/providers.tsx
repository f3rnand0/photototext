'use client';

import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';
import { logger } from '@/lib/logger';

// Error Boundary Component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('React Error Boundary caught error', error, {
      componentStack: errorInfo.componentStack,
    });
    Sentry.captureException(error, {
      extra: { componentStack: errorInfo.componentStack },
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '20px',
          textAlign: 'center',
        }}>
          <h1 style={{ color: '#dc2626', marginBottom: '10px' }}>Something went wrong</h1>
          <p style={{ color: '#666', marginBottom: '20px' }}>
            Please refresh the page or try again later.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

import React from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    logger.info('PhotoToText app initialized', {
      apiUrl: process.env.NEXT_PUBLIC_API_URL,
      debugMode: process.env.NEXT_PUBLIC_DEBUG,
      hasSentry: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
    });
  }, []);

  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}