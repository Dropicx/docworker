/**
 * Duplicate Step Modal Component
 *
 * Simple modal for duplicating a pipeline step with:
 * - New step name input (pre-filled with "Copy of {original}")
 * - Source language dropdown
 */

import React, { useState, useEffect } from 'react';
import { X, Copy, Loader2, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PipelineStep } from '../../types/pipeline';

interface DuplicateStepModalProps {
  isOpen: boolean;
  onClose: () => void;
  originalStep: PipelineStep;
  onDuplicate: (newName: string, sourceLanguage: string | null) => Promise<void>;
}

const DuplicateStepModal: React.FC<DuplicateStepModalProps> = ({
  isOpen,
  onClose,
  originalStep,
  onDuplicate,
}) => {
  const { t } = useTranslation();
  const [newName, setNewName] = useState('');
  const [sourceLanguage, setSourceLanguage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Initialize form when modal opens
  useEffect(() => {
    if (isOpen && originalStep) {
      setNewName(t('pipeline.copyOf', { name: originalStep.name }));
      setSourceLanguage(originalStep.source_language || null);
      setError('');
    }
  }, [isOpen, originalStep, t]);

  const handleDuplicate = async () => {
    if (!newName.trim()) {
      setError(t('pipeline.nameRequired', 'Name ist erforderlich'));
      return;
    }

    setSaving(true);
    setError('');

    try {
      await onDuplicate(newName.trim(), sourceLanguage);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !saving) {
      handleDuplicate();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-primary-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
              <Copy className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-primary-900">
                {t('pipeline.duplicateStepTitle', 'Schritt duplizieren')}
              </h2>
              <p className="text-sm text-primary-600">{originalStep.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-primary-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-primary-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Error Message */}
          {error && (
            <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg text-error-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Step Name Input */}
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2">
              {t('pipeline.newStepName', 'Name des neuen Schritts')} *
            </label>
            <input
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
              placeholder={t('pipeline.copyOf', { name: originalStep.name })}
              autoFocus
            />
          </div>

          {/* Source Language Dropdown */}
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2">
              {t('pipeline.sourceLanguage', 'Quellsprache')}
            </label>
            <select
              value={sourceLanguage || ''}
              onChange={e => setSourceLanguage(e.target.value || null)}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
            >
              <option value="">{t('pipeline.universalLanguage', 'Universal (alle Sprachen)')}</option>
              <option value="de">{t('pipeline.germanOnly', 'Nur Deutsch (German input)')}</option>
              <option value="en">{t('pipeline.englishOnly', 'Nur Englisch (English input)')}</option>
            </select>
          </div>

          {/* Hint */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-700">
              {t(
                'pipeline.duplicateStepHint',
                'Die Kopie wird mit allen Einstellungen des Originalschritts erstellt, jedoch deaktiviert.'
              )}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-primary-200 bg-neutral-50">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-primary-700 hover:bg-primary-100 rounded-lg transition-colors disabled:opacity-50"
          >
            {t('common.cancel', 'Abbrechen')}
          </button>
          <button
            onClick={handleDuplicate}
            disabled={saving || !newName.trim()}
            className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            <span>{t('pipeline.duplicate', 'Duplizieren')}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DuplicateStepModal;
