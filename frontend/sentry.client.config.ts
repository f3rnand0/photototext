import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
const DEBUG = process.env.NEXT_PUBLIC_DEBUG === 'true';

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    
    // Only enable in production or when explicitly debugging
    enabled: !DEBUG || process.env.NODE_ENV === 'production',
    
    // Set environment
    environment: DEBUG ? 'development' : 'production',
    
    // Adjust sample rates based on DEBUG mode
    tracesSampleRate: DEBUG ? 1.0 : 0.1, // 100% in debug, 10% in production
    
    // Replay sampling (session and error-based)
    replaysSessionSampleRate: DEBUG ? 1.0 : 0.1,
    replaysOnErrorSampleRate: 1.0, // Always capture replays on errors
    
    // Integrations
    integrations: [
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],
    
    // Before send - add breadcrumbs for context
    beforeSend(event) {
      // Add any global context here if needed
      return event;
    },
    
    // Debug mode for Sentry SDK
    debug: DEBUG,
  });
  
  if (DEBUG) {
    console.log('[Sentry] Initialized successfully');
  }
} else if (DEBUG) {
  console.warn('[Sentry] No DSN provided, skipping initialization');
}
