import Swal from 'sweetalert2';

/**
 * Show success alert
 */
export const showSuccess = (title, message = '', options = {}) => {
  return Swal.fire({
    icon: 'success',
    title: title,
    text: message,
    showConfirmButton: false,
    timer: options.timer || 100,
    timerProgressBar: true,
    ...options,
  });
};

/**
 * Show error alert
 */
export const showError = (title, message = '', options = {}) => {
  return Swal.fire({
    icon: 'error',
    title: title,
    text: message,
    showConfirmButton: false,
    timer: options.timer || 100,
    timerProgressBar: true,
    ...options,
  });
};

/**
 * Show warning alert
 */
export const showWarning = (title, message = '', options = {}) => {
  return Swal.fire({
    icon: 'warning',
    title: title,
    text: message,
    showConfirmButton: false,
    timer: options.timer || 100,
    timerProgressBar: true,
    ...options,
  });
};

/**
 * Show info alert
 */
export const showInfo = (title, message = '', options = {}) => {
  return Swal.fire({
    icon: 'info',
    title: title,
    text: message,
    showConfirmButton: false,
    timer: options.timer || 100,
    timerProgressBar: true,
    ...options,
  });
};

/**
 * Show confirmation dialog
 */
export const showConfirm = (title, message = '', options = {}) => {
  return Swal.fire({
    icon: 'question',
    title: title,
    text: message,
    showCancelButton: true,
    confirmButtonColor: '#9333ea',
    cancelButtonColor: '#6b7280',
    confirmButtonText: options.confirmText || 'Yes',
    cancelButtonText: options.cancelText || 'No',
    ...options,
  });
};

/**
 * Show loading alert
 */
export const showLoading = (title = 'Loading...', message = '') => {
  Swal.fire({
    title: title,
    text: message,
    allowOutsideClick: false,
    allowEscapeKey: false,
    didOpen: () => {
      Swal.showLoading();
    },
  });
};

/**
 * Close current alert
 */
export const closeAlert = () => {
  Swal.close();
};

export default {
  showSuccess,
  showError,
  showWarning,
  showInfo,
  showConfirm,
  showLoading,
  closeAlert,
};

