const AUTH_URL = `http://localhost`;
const ML_URL = `http://localhost`;

async function request(endpoint, options = {}) {
  // Récupération dynamique du token
  const token = localStorage.getItem('token');
  
  // Automagical routing based on endpoint prefix - nginx will proxy to the right backend
  const baseUrl = AUTH_URL;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Ajout du token si présent
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  const response = await fetch(`${baseUrl}${endpoint}`, config);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Une erreur est survenue');
  }

  return response.json();
}

export const apiClient = {
  get: (endpoint) => request(endpoint, { method: 'GET' }),
  post: (endpoint, body) => request(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  put: (endpoint, body) => request(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
};
