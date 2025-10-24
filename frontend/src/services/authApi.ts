import axios, { AxiosResponse } from 'axios';
import { User, AuthTokens } from '../contexts/AuthContext';

// Base API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const authApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
authApi.interceptors.request.use(config => {
  console.log(`🔐 Auth API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
authApi.interceptors.response.use(
  response => {
    console.log(`✅ Auth API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  error => {
    console.error(
      `❌ Auth API Error: ${error.response?.status} ${error.config?.url}`,
      error.response?.data
    );

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Authentication error';

    throw new Error(message);
  }
);

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export class AuthApiService {
  // Login user
  static async login(email: string, password: string): Promise<LoginResponse> {
    const response: AxiosResponse<LoginResponse> = await authApi.post('/auth/login', {
      email,
      password,
    });
    return response.data;
  }

  // Refresh access token
  static async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    const response: AxiosResponse<RefreshTokenResponse> = await authApi.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  // Logout user
  static async logout(refreshToken: string): Promise<void> {
    await authApi.post('/auth/logout', {
      refresh_token: refreshToken,
    });
  }

  // Get current user info
  static async getCurrentUser(accessToken: string): Promise<User> {
    const response: AxiosResponse<User> = await authApi.get('/auth/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    return response.data;
  }

  // Change password
  static async changePassword(
    accessToken: string,
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    await authApi.post(
      '/auth/change-password',
      {
        current_password: currentPassword,
        new_password: newPassword,
      },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );
  }
}

// Export individual functions for easier use
export const authApi = {
  login: AuthApiService.login,
  refreshToken: AuthApiService.refreshToken,
  logout: AuthApiService.logout,
  getCurrentUser: AuthApiService.getCurrentUser,
  changePassword: AuthApiService.changePassword,
};

export default AuthApiService;
