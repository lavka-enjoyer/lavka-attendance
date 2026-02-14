/**
 * Toast notification component using Sonner.
 * Provides feedback for successful actions, errors, etc.
 */
import { Toaster as SonnerToaster, toast } from 'sonner';

/**
 * Toaster container component.
 * Should be placed at the root of the app.
 */
export function Toaster() {
  return (
    <SonnerToaster
      position="top-center"
      toastOptions={{
        style: {
          fontFamily: 'var(--pixel-font)',
          border: '2px solid black',
          boxShadow: '3px 3px 0px 0px rgba(0,0,0,1)',
          borderRadius: '0px',
        },
        className: 'pixel-toast',
      }}
      theme="light"
      richColors
    />
  );
}

/**
 * Show a success toast notification.
 * @param {string} message - The message to display
 * @param {Object} options - Additional toast options
 */
export function showSuccess(message, options = {}) {
  toast.success(message, {
    duration: 3000,
    ...options,
  });
}

/**
 * Show an error toast notification.
 * @param {string} message - The error message to display
 * @param {Object} options - Additional toast options
 */
export function showError(message, options = {}) {
  toast.error(message, {
    duration: 4000,
    ...options,
  });
}

/**
 * Show an info toast notification.
 * @param {string} message - The info message to display
 * @param {Object} options - Additional toast options
 */
export function showInfo(message, options = {}) {
  toast.info(message, {
    duration: 3000,
    ...options,
  });
}

/**
 * Show a warning toast notification.
 * @param {string} message - The warning message to display
 * @param {Object} options - Additional toast options
 */
export function showWarning(message, options = {}) {
  toast.warning(message, {
    duration: 4000,
    ...options,
  });
}

/**
 * Show a loading toast that can be updated later.
 * @param {string} message - The loading message to display
 * @returns {string|number} Toast ID for later updates
 */
export function showLoading(message) {
  return toast.loading(message);
}

/**
 * Update an existing toast.
 * @param {string|number} toastId - The ID of the toast to update
 * @param {Object} options - New toast options
 */
export function updateToast(toastId, options) {
  toast.dismiss(toastId);
  if (options.type === 'success') {
    toast.success(options.message, { duration: 3000 });
  } else if (options.type === 'error') {
    toast.error(options.message, { duration: 4000 });
  } else {
    toast(options.message, { duration: 3000 });
  }
}

/**
 * Dismiss a toast.
 * @param {string|number} toastId - The ID of the toast to dismiss
 */
export function dismissToast(toastId) {
  toast.dismiss(toastId);
}

// Re-export toast for direct usage
export { toast };
