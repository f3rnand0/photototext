type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

class Logger {
  private isDebugEnabled: boolean;
  private component: string;
  private breadcrumbs: Array<{ message: string; timestamp: string; data?: unknown }> = [];
  private maxBreadcrumbs = 50;

  constructor(component: string) {
    this.component = component;
    this.isDebugEnabled = process.env.NEXT_PUBLIC_DEBUG === 'true';
  }

  private formatMessage(level: LogLevel, message: string, context?: Record<string, unknown>): string {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` | ${JSON.stringify(context)}` : '';
    return `[${timestamp}] [${this.component}] [${level.toUpperCase()}] ${message}${contextStr}`;
  }

  private log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    if (level === 'debug' && !this.isDebugEnabled) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
    };

    // Always add to breadcrumbs for Sentry
    this.addBreadcrumb(message, level, context);

    // Console output only in debug mode or for errors
    if (this.isDebugEnabled || level === 'error' || level === 'warn') {
      const formattedMessage = this.formatMessage(level, message, context);
      
      switch (level) {
        case 'debug':
          console.debug(formattedMessage);
          break;
        case 'info':
          console.info(formattedMessage);
          break;
        case 'warn':
          console.warn(formattedMessage);
          break;
        case 'error':
          console.error(formattedMessage);
          break;
      }
    }

    // Send errors to Sentry if available
    if (level === 'error' && typeof window !== 'undefined' && (window as unknown as { Sentry?: { captureException: (err: Error) => void } }).Sentry) {
      const error = new Error(message);
      (window as unknown as { Sentry: { captureException: (err: Error) => void } }).Sentry.captureException(error);
    }
  }

  private addBreadcrumb(message: string, level: LogLevel, data?: Record<string, unknown>): void {
    this.breadcrumbs.push({
      message,
      timestamp: new Date().toISOString(),
      data: { level, ...data },
    });

    // Keep only last N breadcrumbs
    if (this.breadcrumbs.length > this.maxBreadcrumbs) {
      this.breadcrumbs.shift();
    }
  }

  debug(message: string, context?: Record<string, unknown>): void {
    this.log('debug', message, context);
  }

  info(message: string, context?: Record<string, unknown>): void {
    this.log('info', message, context);
  }

  warn(message: string, context?: Record<string, unknown>): void {
    this.log('warn', message, context);
  }

  error(message: string, error?: Error, context?: Record<string, unknown>): void {
    const errorContext = error
      ? { ...context, errorName: error.name, errorMessage: error.message, stack: error.stack }
      : context;
    this.log('error', message, errorContext);
  }

  getBreadcrumbs(): Array<{ message: string; timestamp: string; data?: unknown }> {
    return [...this.breadcrumbs];
  }

  clearBreadcrumbs(): void {
    this.breadcrumbs = [];
  }
}

// Export factory function
export function createLogger(component: string): Logger {
  return new Logger(component);
}

// Default logger instance
export const logger = createLogger('PhotoToText');

export default logger;
