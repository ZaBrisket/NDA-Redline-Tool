'use client';

import { useState } from 'react';
import { Check, X, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface ChecklistRule {
  title: string;
  requirement: string;
  description: string;
  why: string;
  standard_language: string;
}

interface Redline {
  id: string;
  clause_type: string;
  start: number;
  end: number;
  original_text: string;
  revised_text: string;
  severity: 'critical' | 'high' | 'moderate' | 'low';
  confidence: number;
  source: string;
  explanation: string;
  user_decision: 'accept' | 'reject' | null;
  checklist_rule: ChecklistRule;
}

interface Props {
  redlines: Redline[];
  onDecisionChange: (redlineId: string, decision: 'accept' | 'reject') => void;
}

export default function RedlineReviewer({ redlines, onDecisionChange }: Props) {
  const [selectedRedline, setSelectedRedline] = useState<string | null>(
    redlines.length > 0 ? redlines[0].id : null
  );
  const [expandedDetails, setExpandedDetails] = useState<string | null>(null);

  const selectedRedlineData = redlines.find(r => r.id === selectedRedline);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'moderate': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    return severity === 'critical' || severity === 'high'
      ? <AlertTriangle className="w-4 h-4" />
      : <Info className="w-4 h-4" />;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Document with redlines highlighted */}
        <div className="col-span-7 bg-white rounded-lg shadow-sm border border-gray-200 p-6 max-h-[calc(100vh-200px)] overflow-y-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <span className="mr-2">📄</span>
            Document with Redlines
          </h2>

          <div className="prose max-w-none">
            {redlines.map((redline, index) => (
              <div
                key={redline.id}
                className={`
                  my-4 p-4 rounded-lg border-2 cursor-pointer transition-all
                  ${selectedRedline === redline.id
                    ? 'ring-2 ring-blue-500 border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
                onClick={() => setSelectedRedline(redline.id)}
              >
                {/* Redline number and severity */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-500">
                    REDLINE #{index + 1}
                  </span>
                  <span className={`
                    text-xs px-2 py-1 rounded-full font-medium border
                    ${getSeverityColor(redline.severity)}
                  `}>
                    {redline.severity.toUpperCase()}
                  </span>
                </div>

                {/* Original text (strikethrough) */}
                {redline.original_text && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-500 mb-1">Original:</div>
                    <div className="line-through text-red-700 bg-red-50 p-2 rounded">
                      {redline.original_text}
                    </div>
                  </div>
                )}

                {/* Revised text (underline/highlight) */}
                {redline.revised_text && (
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Proposed:</div>
                    <div className="text-green-700 bg-green-50 p-2 rounded border-l-4 border-green-500">
                      {redline.revised_text}
                    </div>
                  </div>
                )}

                {/* Decision indicators */}
                {redline.user_decision && (
                  <div className="mt-2 flex items-center space-x-2">
                    {redline.user_decision === 'accept' ? (
                      <>
                        <Check className="w-4 h-4 text-green-600" />
                        <span className="text-sm text-green-600 font-medium">Accepted</span>
                      </>
                    ) : (
                      <>
                        <X className="w-4 h-4 text-red-600" />
                        <span className="text-sm text-red-600 font-medium">Rejected</span>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}

            {redlines.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No redlines found
              </div>
            )}
          </div>
        </div>

        {/* Right: Checklist rule details and accept/reject */}
        <div className="col-span-5 space-y-4">
          {selectedRedlineData ? (
            <>
              {/* Checklist Rule Card */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {selectedRedlineData.checklist_rule.title}
                    </h3>
                    <div className={`
                      inline-flex items-center space-x-1 mt-2 px-2 py-1 rounded-full text-xs font-medium border
                      ${getSeverityColor(selectedRedlineData.severity)}
                    `}>
                      {getSeverityIcon(selectedRedlineData.severity)}
                      <span>{selectedRedlineData.severity.toUpperCase()} PRIORITY</span>
                    </div>
                  </div>
                </div>

                {/* Requirement */}
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="text-xs font-semibold text-blue-900 mb-1">
                    EDGEWATER REQUIREMENT
                  </div>
                  <div className="text-sm text-blue-800">
                    {selectedRedlineData.checklist_rule.requirement}
                  </div>
                </div>

                {/* Description */}
                <div className="mb-4">
                  <div className="text-xs font-semibold text-gray-700 mb-2">
                    WHAT THIS MEANS
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {selectedRedlineData.checklist_rule.description}
                  </p>
                </div>

                {/* Why this matters */}
                <div className="mb-4">
                  <div className="text-xs font-semibold text-gray-700 mb-2">
                    WHY THIS MATTERS
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {selectedRedlineData.checklist_rule.why}
                  </p>
                </div>

                {/* Standard Language (expandable) */}
                {selectedRedlineData.checklist_rule.standard_language !== 'N/A' &&
                 selectedRedlineData.checklist_rule.standard_language !== 'Varies' &&
                 selectedRedlineData.checklist_rule.standard_language !== 'Varies based on specific clause' && (
                  <div className="border border-gray-200 rounded-lg">
                    <button
                      onClick={() => setExpandedDetails(
                        expandedDetails === selectedRedlineData.id ? null : selectedRedlineData.id
                      )}
                      className="w-full px-3 py-2 flex items-center justify-between text-xs font-semibold text-gray-700 hover:bg-gray-50"
                    >
                      <span>STANDARD LANGUAGE</span>
                      {expandedDetails === selectedRedlineData.id ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                    {expandedDetails === selectedRedlineData.id && (
                      <div className="px-3 py-2 text-sm text-gray-600 bg-gray-50 border-t border-gray-200 whitespace-pre-wrap">
                        {selectedRedlineData.checklist_rule.standard_language}
                      </div>
                    )}
                  </div>
                )}

                {/* Confidence & Source */}
                <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
                  <span>Source: {selectedRedlineData.source.toUpperCase()}</span>
                  <span>Confidence: {selectedRedlineData.confidence}%</span>
                </div>
              </div>

              {/* Accept/Reject Buttons */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-sm font-semibold text-gray-900 mb-4">
                  Your Decision
                </div>

                <div className="space-y-3">
                  <button
                    onClick={() => onDecisionChange(selectedRedlineData.id, 'accept')}
                    className={`
                      w-full flex items-center justify-center space-x-2 px-4 py-3 rounded-lg border-2 transition-all
                      ${selectedRedlineData.user_decision === 'accept'
                        ? 'bg-green-600 border-green-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-green-500 hover:bg-green-50'
                      }
                    `}
                  >
                    <Check className="w-5 h-5" />
                    <span className="font-medium">Accept Redline</span>
                  </button>

                  <button
                    onClick={() => onDecisionChange(selectedRedlineData.id, 'reject')}
                    className={`
                      w-full flex items-center justify-center space-x-2 px-4 py-3 rounded-lg border-2 transition-all
                      ${selectedRedlineData.user_decision === 'reject'
                        ? 'bg-red-600 border-red-600 text-white'
                        : 'bg-white border-gray-300 text-gray-700 hover:border-red-500 hover:bg-red-50'
                      }
                    `}
                  >
                    <X className="w-5 h-5" />
                    <span className="font-medium">Reject Redline</span>
                  </button>
                </div>

                {selectedRedlineData.user_decision && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
                    <div className="text-xs text-gray-500">
                      Decision saved • Click the buttons above to change
                    </div>
                  </div>
                )}
              </div>

              {/* Navigation */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between text-sm">
                  <button
                    onClick={() => {
                      const currentIndex = redlines.findIndex(r => r.id === selectedRedline);
                      if (currentIndex > 0) {
                        setSelectedRedline(redlines[currentIndex - 1].id);
                      }
                    }}
                    disabled={redlines.findIndex(r => r.id === selectedRedline) === 0}
                    className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded disabled:text-gray-400 disabled:hover:bg-transparent"
                  >
                    ← Previous
                  </button>

                  <span className="text-gray-600">
                    {redlines.findIndex(r => r.id === selectedRedline) + 1} of {redlines.length}
                  </span>

                  <button
                    onClick={() => {
                      const currentIndex = redlines.findIndex(r => r.id === selectedRedline);
                      if (currentIndex < redlines.length - 1) {
                        setSelectedRedline(redlines[currentIndex + 1].id);
                      }
                    }}
                    disabled={redlines.findIndex(r => r.id === selectedRedline) === redlines.length - 1}
                    className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded disabled:text-gray-400 disabled:hover:bg-transparent"
                  >
                    Next →
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center text-gray-500">
              Select a redline to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
