/**
 * User Management Component
 * Admin dashboard for managing users: create, edit, deactivate, delete, reset passwords
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Users,
  UserPlus,
  Loader2,
  AlertCircle,
  RefreshCw,
  Shield,
  User,
  Mail,
  Key,
  Trash2,
  UserCheck,
  UserX,
  MoreVertical,
  X,
  Check,
  Eye,
  EyeOff,
} from 'lucide-react';
import { userApi, User as UserType, UserRole, UserStats } from '../../services/userApi';
import { useAuth } from '../../contexts/AuthContext';

type ModalType = 'create' | 'edit' | 'resetPassword' | 'delete' | null;

export default function UserManagement() {
  const { tokens, user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserType[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modal state
  const [modalType, setModalType] = useState<ModalType>(null);
  const [selectedUser, setSelectedUser] = useState<UserType | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'user' as UserRole,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Dropdown state
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  // Sync token
  useEffect(() => {
    if (tokens?.access_token) {
      userApi.updateToken(tokens.access_token);
    }
  }, [tokens]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [usersRes, statsRes] = await Promise.all([userApi.listUsers(), userApi.getStats()]);
      setUsers(usersRes.users);
      setStats(statsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Benutzer');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setOpenDropdown(null);
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const openModal = (type: ModalType, user?: UserType) => {
    setModalType(type);
    setSelectedUser(user || null);
    setFormError(null);
    setShowPassword(false);

    if (type === 'edit' && user) {
      setFormData({
        email: user.email,
        password: '',
        full_name: user.full_name,
        role: user.role,
      });
    } else {
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role: 'user',
      });
    }
  };

  const closeModal = () => {
    setModalType(null);
    setSelectedUser(null);
    setFormError(null);
  };

  const handleCreateUser = async () => {
    if (!formData.email || !formData.password || !formData.full_name) {
      setFormError('Bitte alle Felder ausfüllen');
      return;
    }
    if (formData.password.length < 8) {
      setFormError('Passwort muss mindestens 8 Zeichen haben');
      return;
    }

    try {
      setActionLoading('create');
      await userApi.createUser(formData);
      closeModal();
      loadData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Erstellen');
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;

    try {
      setActionLoading('update');
      await userApi.updateUser(selectedUser.id, {
        email: formData.email !== selectedUser.email ? formData.email : undefined,
        full_name: formData.full_name !== selectedUser.full_name ? formData.full_name : undefined,
        role: formData.role !== selectedUser.role ? formData.role : undefined,
      });
      closeModal();
      loadData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Aktualisieren');
    } finally {
      setActionLoading(null);
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser || !formData.password) {
      setFormError('Bitte neues Passwort eingeben');
      return;
    }
    if (formData.password.length < 8) {
      setFormError('Passwort muss mindestens 8 Zeichen haben');
      return;
    }

    try {
      setActionLoading('reset');
      await userApi.resetPassword(selectedUser.id, formData.password);
      closeModal();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Zurücksetzen');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    try {
      setActionLoading('delete');
      await userApi.deleteUser(selectedUser.id);
      closeModal();
      loadData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Löschen');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (user: UserType) => {
    try {
      setActionLoading(user.id);
      if (user.is_active) {
        await userApi.deactivateUser(user.id);
      } else {
        await userApi.activateUser(user.id);
      }
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Aktion fehlgeschlagen');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Users className="w-6 h-6 text-brand-600" />
          <h2 className="text-xl font-bold text-neutral-900">Benutzerverwaltung</h2>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadData}
            className="p-2 text-neutral-600 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
            title="Aktualisieren"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={() => openModal('create')}
            className="flex items-center space-x-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            <span>Neuer Benutzer</span>
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center space-x-2 p-4 bg-error-50 border border-error-200 rounded-lg text-error-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-neutral-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-neutral-900">{stats.total_users}</div>
            <div className="text-sm text-neutral-600">Gesamt</div>
          </div>
          <div className="bg-success-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-success-700">{stats.active_users}</div>
            <div className="text-sm text-success-600">Aktiv</div>
          </div>
          <div className="bg-brand-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-brand-700">{stats.admin_users}</div>
            <div className="text-sm text-brand-600">Admins</div>
          </div>
          <div className="bg-neutral-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-neutral-700">{stats.user_users}</div>
            <div className="text-sm text-neutral-600">Benutzer</div>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">
                  Benutzer
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Rolle</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">Status</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-neutral-700">
                  Letzter Login
                </th>
                <th className="text-right px-4 py-3 text-sm font-medium text-neutral-700">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {users.map(user => {
                const isCurrentUser = user.id === currentUser?.id;
                return (
                  <tr
                    key={user.id}
                    className={`hover:bg-neutral-50 ${!user.is_active ? 'opacity-60' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-3">
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            user.role === 'admin' ? 'bg-brand-100' : 'bg-neutral-100'
                          }`}
                        >
                          {user.role === 'admin' ? (
                            <Shield className="w-5 h-5 text-brand-600" />
                          ) : (
                            <User className="w-5 h-5 text-neutral-600" />
                          )}
                        </div>
                        <div>
                          <div className="font-medium text-neutral-900">
                            {user.full_name}
                            {isCurrentUser && (
                              <span className="ml-2 text-xs text-brand-600">(Sie)</span>
                            )}
                          </div>
                          <div className="text-sm text-neutral-500">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          user.role === 'admin'
                            ? 'bg-brand-100 text-brand-700'
                            : 'bg-neutral-100 text-neutral-700'
                        }`}
                      >
                        {user.role === 'admin' ? 'Admin' : 'Benutzer'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          user.is_active
                            ? 'bg-success-100 text-success-700'
                            : 'bg-error-100 text-error-700'
                        }`}
                      >
                        {user.is_active ? 'Aktiv' : 'Inaktiv'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-neutral-600">
                      {formatDate(user.last_login_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="relative">
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setOpenDropdown(openDropdown === user.id ? null : user.id);
                          }}
                          disabled={actionLoading === user.id}
                          className="p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors"
                        >
                          {actionLoading === user.id ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                          ) : (
                            <MoreVertical className="w-5 h-5" />
                          )}
                        </button>

                        {openDropdown === user.id && (
                          <div className="absolute right-0 mt-1 w-48 bg-white border border-neutral-200 rounded-lg shadow-lg z-10">
                            <button
                              onClick={() => {
                                setOpenDropdown(null);
                                openModal('edit', user);
                              }}
                              className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                            >
                              <Mail className="w-4 h-4" />
                              <span>Bearbeiten</span>
                            </button>
                            <button
                              onClick={() => {
                                setOpenDropdown(null);
                                openModal('resetPassword', user);
                              }}
                              className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                            >
                              <Key className="w-4 h-4" />
                              <span>Passwort zurücksetzen</span>
                            </button>
                            {!isCurrentUser && (
                              <>
                                <button
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    handleToggleActive(user);
                                  }}
                                  className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                                >
                                  {user.is_active ? (
                                    <>
                                      <UserX className="w-4 h-4" />
                                      <span>Deaktivieren</span>
                                    </>
                                  ) : (
                                    <>
                                      <UserCheck className="w-4 h-4" />
                                      <span>Aktivieren</span>
                                    </>
                                  )}
                                </button>
                                <hr className="my-1 border-neutral-200" />
                                <button
                                  onClick={() => {
                                    setOpenDropdown(null);
                                    openModal('delete', user);
                                  }}
                                  className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-error-600 hover:bg-error-50"
                                >
                                  <Trash2 className="w-4 h-4" />
                                  <span>Löschen</span>
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {users.length === 0 && (
          <div className="text-center py-12 text-neutral-500">Keine Benutzer gefunden</div>
        )}
      </div>

      {/* Modals */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={closeModal} />
          <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-neutral-900">
                {modalType === 'create' && 'Neuer Benutzer'}
                {modalType === 'edit' && 'Benutzer bearbeiten'}
                {modalType === 'resetPassword' && 'Passwort zurücksetzen'}
                {modalType === 'delete' && 'Benutzer löschen'}
              </h3>
              <button
                onClick={closeModal}
                className="p-2 text-neutral-400 hover:text-neutral-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form Error */}
            {formError && (
              <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-lg text-error-700 text-sm">
                {formError}
              </div>
            )}

            {/* Create/Edit Form */}
            {(modalType === 'create' || modalType === 'edit') && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                    placeholder="Max Mustermann"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">E-Mail</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                    placeholder="max@example.com"
                  />
                </div>
                {modalType === 'create' && (
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">
                      Passwort
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={e => setFormData({ ...formData, password: e.target.value })}
                        className="w-full px-3 py-2 pr-10 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                        placeholder="Min. 8 Zeichen"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600"
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Rolle</label>
                  <select
                    value={formData.role}
                    onChange={e => setFormData({ ...formData, role: e.target.value as UserRole })}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                  >
                    <option value="user">Benutzer</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={modalType === 'create' ? handleCreateUser : handleUpdateUser}
                    disabled={!!actionLoading}
                    className="flex items-center space-x-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4" />
                    )}
                    <span>{modalType === 'create' ? 'Erstellen' : 'Speichern'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Reset Password Form */}
            {modalType === 'resetPassword' && selectedUser && (
              <div className="space-y-4">
                <p className="text-sm text-neutral-600">
                  Neues Passwort für <strong>{selectedUser.full_name}</strong> ({selectedUser.email}
                  ) festlegen.
                </p>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Neues Passwort
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={e => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-3 py-2 pr-10 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                      placeholder="Min. 8 Zeichen"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={handleResetPassword}
                    disabled={!!actionLoading}
                    className="flex items-center space-x-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Key className="w-4 h-4" />
                    )}
                    <span>Passwort setzen</span>
                  </button>
                </div>
              </div>
            )}

            {/* Delete Confirmation */}
            {modalType === 'delete' && selectedUser && (
              <div className="space-y-4">
                <div className="p-4 bg-error-50 border border-error-200 rounded-lg">
                  <p className="text-error-700">
                    Sind Sie sicher, dass Sie <strong>{selectedUser.full_name}</strong> (
                    {selectedUser.email}) löschen möchten?
                  </p>
                  <p className="text-sm text-error-600 mt-2">
                    Der Benutzer wird deaktiviert und kann sich nicht mehr anmelden.
                  </p>
                </div>
                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={handleDeleteUser}
                    disabled={!!actionLoading}
                    className="flex items-center space-x-2 px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700 transition-colors disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    <span>Löschen</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
