// Development authentication helper
// This sets a valid token for testing purposes

const DEV_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZDgzMWU1MC1lY2Y5LTRjOGQtODlmYS1jNjU0NTg4ZjYwN2MiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoidXNlciIsInN1YnNjcmlwdGlvbl90aWVyIjoiZnJlZSIsImlhdCI6MTc1NjA1MTQyNiwiZXhwIjoxNzU2MDUzMjI2LCJqdGkiOiJhZ2lMQjN0RFhnLUwxamtjMkRwZXVSQmVldFgtdTdSSkZ0RFpmNE02dGprIiwidHlwZSI6ImFjY2Vzc190b2tlbiJ9.HQKcvZZGhwpspeRmcEIRsvO4p5zg1XJyBrLEkcp2HdQ";

// Set the token in localStorage for development
if (process.env.NODE_ENV === 'development') {
  localStorage.setItem('access_token', DEV_ACCESS_TOKEN);
  console.log('Development authentication token set');
}