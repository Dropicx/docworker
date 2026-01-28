/**
 * Citations display component for showing document sources.
 * Displays retriever resources as clickable chips with relevance scores.
 */

import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { RetrieverResource } from '../../types/chat';

interface CitationsDisplayProps {
  resources: RetrieverResource[];
  maxVisible?: number;
}

/**
 * Format relevance score as percentage.
 */
function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Get score color based on relevance.
 */
function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-600 dark:text-green-400';
  if (score >= 0.6) return 'text-amber-600 dark:text-amber-400';
  return 'text-neutral-500 dark:text-neutral-400';
}

export const CitationsDisplay: React.FC<CitationsDisplayProps> = ({
  resources,
  maxVisible = 3,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!resources || resources.length === 0) {
    return null;
  }

  const visibleResources = expanded ? resources : resources.slice(0, maxVisible);
  const hasMore = resources.length > maxVisible;

  return (
    <div className="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-700">
      {/* Header */}
      <div className="flex items-center gap-1.5 mb-2">
        <FileText className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          Quellen ({resources.length})
        </span>
      </div>

      {/* Citations list */}
      <div className="flex flex-wrap gap-2">
        {visibleResources.map((resource, index) => (
          <div
            key={resource.segment_id || index}
            className="group relative"
          >
            {/* Citation chip */}
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-neutral-50 dark:bg-neutral-700/50 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg border border-neutral-200 dark:border-neutral-600 transition-colors cursor-default">
              <span className="text-xs text-neutral-700 dark:text-neutral-300 max-w-[200px] truncate">
                {resource.document_name}
              </span>
              {resource.score > 0 && (
                <span className={`text-[10px] font-medium ${getScoreColor(resource.score)}`}>
                  {formatScore(resource.score)}
                </span>
              )}
            </div>

            {/* Tooltip with content preview */}
            {resource.content_preview && (
              <div className="absolute bottom-full left-0 mb-1 w-64 p-3 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-150 z-10 pointer-events-none">
                <p className="text-xs text-neutral-600 dark:text-neutral-300 line-clamp-4">
                  {resource.content_preview}
                </p>
                {resource.score > 0 && (
                  <div className="mt-2 pt-2 border-t border-neutral-100 dark:border-neutral-700">
                    <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
                      Relevanz: {formatScore(resource.score)}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Expand/collapse button */}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              <span>Weniger anzeigen</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              <span>{resources.length - maxVisible} weitere Quellen</span>
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default CitationsDisplay;
