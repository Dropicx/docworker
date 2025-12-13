/**
 * User Management API Service
 * Admin-only endpoints for managing users
 */

const API_BASE = '/api/users';

export type UserRole = 'user' | 'admin';
export type UserStatus = 'active' | 'inactive' | 'pending' | 'suspended';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  created_by_admin_id: string | null;
}

export interface UserListResponse {
  users: User[];
  total: number;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  role?: UserRole;
  status?: UserStatus;
}

export interface ResetPasswordRequest {
  new_password: string;
}

export interface UserStats {
  total_users: number;
  active_users: number;
  admin_users: number;
  user_users: number;
}

class UserApiService {
  private token: string | null = null;

  updateToken(token: string) {
    this.token = token;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  async listUsers(
    skip = 0,
    limit = 100,
    roleFilter?: UserRole,
    statusFilter?: UserStatus
  ): Promise<UserListResponse> {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (roleFilter) params.append('role_filter', roleFilter);
    if (statusFilter) params.append('status_filter', statusFilter);

    const response = await fetch(`${API_BASE}?${params}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<UserListResponse>(response);
  }

  async getUser(userId: string): Promise<User> {
    const response = await fetch(`${API_BASE}/${userId}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<User>(response);
  }

  async createUser(data: CreateUserRequest): Promise<User> {
    const response = await fetch(API_BASE, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    return this.handleResponse<User>(response);
  }

  async updateUser(userId: string, data: UpdateUserRequest): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/${userId}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    return this.handleResponse<{ message: string }>(response);
  }

  async deleteUser(userId: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/${userId}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });
    return this.handleResponse<{ message: string }>(response);
  }

  async activateUser(userId: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/${userId}/activate`, {
      method: 'PATCH',
      headers: this.getHeaders(),
    });
    return this.handleResponse<{ message: string }>(response);
  }

  async deactivateUser(userId: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/${userId}/deactivate`, {
      method: 'PATCH',
      headers: this.getHeaders(),
    });
    return this.handleResponse<{ message: string }>(response);
  }

  async resetPassword(userId: string, newPassword: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/${userId}/reset-password`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ new_password: newPassword }),
    });
    return this.handleResponse<{ message: string }>(response);
  }

  async getStats(): Promise<UserStats> {
    const response = await fetch(`${API_BASE}/stats/overview`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<UserStats>(response);
  }
}

export const userApi = new UserApiService();
