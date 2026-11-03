/**
 * The sentence to show for a failed request: the one the API sends (`detail`) when it is a text, else the message of
 * the error. Without it the user reads the text of axios ("Request failed with status code 409").
 */
export function errorMessage(error: any): string {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail) {
    return detail
  }
  // The detail of a task that failed is an object that holds the reason in `status`.
  if (typeof detail?.status === 'string' && detail.status) {
    return detail.status
  }
  return String(error?.message ?? error)
}
