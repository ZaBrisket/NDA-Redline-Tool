'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, Download, ArrowLeft, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import RedlineReviewer from '@/components/RedlineReviewer';

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
  checklist_rule: {
    title: string;
    requirement: string;
    description: string;
    why: string;
    standard_language: string;
  };
}

interface JobData {
  job_id: string;
  status: string;
  progress: number;
  filename: string;
  redlines: Redline[];
  total_redlines: number;
  output_path: string;
}

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [jobData, setJobData] = useState<JobData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    // Subscribe to SSE for real-time updates
    const eventSource = new EventSource(`/api/jobs/${jobId}/events`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.error) {
        setError(data.error);
        setLoading(false);
        eventSource.close();
        return;
      }

      if (data.status === 'complete') {
        fetchJobDetails();
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      fetchJobDetails();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  const fetchJobDetails = async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/status`);

      if (!response.ok) {
        throw new Error('Failed to fetch job details');
      }

      const data = await response.json();
      setJobData(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLoading(false);
    }
  };

  const handleDecisionChange = async (redlineId: string, decision: 'accept' | 'reject') => {
    if (!jobData) return;

    // Update local state immediately
    const updatedRedlines = jobData.redlines.map(r =>
      r.id === redlineId ? { ...r, user_decision: decision } : r
    );

    setJobData({ ...jobData, redlines: updatedRedlines });

    // Send to backend
    try {
      await fetch(`/api/jobs/${jobId}/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decisions: [{ redline_id: redlineId, decision }],
        }),
      });
    } catch (err) {
      console.error('Failed to save decision:', err);
    }
  };

  const handleDownload = async () => {
    if (!jobData) return;

    setDownloading(true);

    try {
      const response = await fetch(`/api/jobs/${jobId}/download?final=true`);

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${jobData.filename.replace('.docx', '')}_reviewed.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download document');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-lg text-gray-600">Processing your NDA...</p>
          <p className="text-sm text-gray-500 mt-2">
            Analyzing against Edgewater checklist
          </p>
        </div>
      </div>
    );
  }

  if (error || !jobData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-lg text-gray-900 mb-2">Error</p>
          <p className="text-gray-600">{error || 'Job not found'}</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Upload
          </button>
        </div>
      </div>
    );
  }

  const acceptedCount = jobData.redlines.filter(r => r.user_decision === 'accept').length;
  const rejectedCount = jobData.redlines.filter(r => r.user_decision === 'reject').length;
  const pendingCount = jobData.total_redlines - acceptedCount - rejectedCount;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/')}
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {jobData.filename}
                </h1>
                <p className="text-sm text-gray-500">
                  {jobData.total_redlines} redlines found
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              {/* Stats */}
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-1">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span className="text-gray-600">{acceptedCount} accepted</span>
                </div>
                <div className="flex items-center space-x-1">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span className="text-gray-600">{rejectedCount} rejected</span>
                </div>
                <div className="flex items-center space-x-1">
                  <AlertCircle className="w-4 h-4 text-yellow-600" />
                  <span className="text-gray-600">{pendingCount} pending</span>
                </div>
              </div>

              {/* Download Button */}
              <button
                onClick={handleDownload}
                disabled={downloading || pendingCount > 0}
                className={`
                  flex items-center space-x-2 px-4 py-2 rounded-lg
                  ${pendingCount === 0
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {downloading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Download className="w-5 h-5" />
                )}
                <span>Download</span>
              </button>
            </div>
          </div>

          {pendingCount > 0 && (
            <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-sm text-yellow-800">
                Please review all {pendingCount} pending redline{pendingCount !== 1 ? 's' : ''} before downloading
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Redline Reviewer */}
      <RedlineReviewer
        redlines={jobData.redlines}
        onDecisionChange={handleDecisionChange}
      />
    </div>
  );
}
