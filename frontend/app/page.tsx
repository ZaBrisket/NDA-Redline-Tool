'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, Loader2 } from 'lucide-react';

export default function UploadPage() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.docx')) {
      alert('Please upload a .docx file');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      router.push(`/review/${data.job_id}`);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file. Please try again.');
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleUpload(e.target.files[0]);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            NDA Reviewer
          </h1>
          <p className="text-lg text-gray-600">
            Automated redlining with Edgewater checklist
          </p>
        </div>

        {/* Upload Area */}
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-12 text-center
            transition-colors duration-200
            ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white'}
            ${uploading ? 'opacity-50 pointer-events-none' : 'hover:border-gray-400'}
          `}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          {uploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-16 h-16 text-blue-600 animate-spin mb-4" />
              <p className="text-lg text-gray-600">
                Uploading and processing...
              </p>
            </div>
          ) : (
            <>
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-700 mb-2">
                Drop your NDA here or click to upload
              </p>
              <p className="text-sm text-gray-500 mb-6">
                Supports .docx files only
              </p>

              <label className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors">
                <Upload className="w-5 h-5 mr-2" />
                Select File
                <input
                  type="file"
                  accept=".docx"
                  className="hidden"
                  onChange={handleChange}
                  disabled={uploading}
                />
              </label>
            </>
          )}
        </div>

        {/* Info */}
        <div className="mt-12 bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            How it works
          </h2>
          <ol className="list-decimal list-inside space-y-2 text-gray-600">
            <li>Upload your NDA document (.docx format)</li>
            <li>AI analyzes against Edgewater's checklist (20+ rules)</li>
            <li>Review all proposed redlines with explanations</li>
            <li>Accept or reject each change</li>
            <li>Download the final redlined document</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
