// Development authentication helper
// This sets a valid token for testing purposes

const DEV_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZmNlZmM5Ny04NzFhLTQ0OTEtODNlNi1mZTY5OWNiZjFjMTkiLCJlbWFpbCI6Im5ld3VzZXJAZXhhbXBsZS5jb20iLCJyb2xlIjoidXNlciIsInN1YnNjcmlwdGlvbl90aWVyIjoiZnJlZSIsImlhdCI6MTc1NjA2NzI0OSwiZXhwIjoxNzU2MDY5MDQ5LCJqdGkiOiJMRUZQbU9uTUdjNzdiRkdvUkJSQTI1M0pXNHRCSUJobXhtbWRUQ0ZOamx3IiwidHlwZSI6ImFjY2Vzc190b2tlbiJ9.D5xl6fRt4dJKxIFTJgW0ZPjslv3MZJOq6rVpRdiy-xI";

// Set the token in localStorage for development
if (process.env.NODE_ENV === 'development') {
  console.log('🔄 CLEARING ALL TOKENS AND SETTING FRESH ONE');
  
  // Force clear ALL tokens first
  localStorage.clear();
  
  // Set fresh token
  localStorage.setItem('access_token', DEV_ACCESS_TOKEN);
  localStorage.setItem('refresh_token', 'dev_refresh_token');
  
  console.log('✅ Fresh token set:', DEV_ACCESS_TOKEN.substring(0, 50) + '...');
  console.log('✅ Token expires at:', new Date(1756069049 * 1000).toLocaleTimeString());  
  console.log('✅ Current time:', new Date().toLocaleTimeString());
  console.log('🔄 If you still see "Network error loading universes", please refresh the page (F5/Ctrl+R)');
}