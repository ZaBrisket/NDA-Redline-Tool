# NDA Reviewer Frontend

Next.js-based frontend for reviewing and approving NDA redlines before export.

## Features

### 📤 Upload Page
- Drag-and-drop file upload
- Real-time upload progress
- File type validation (.docx only)

### 📋 Review Interface
- **Split-pane view**: Document with redlines on left, checklist rules on right
- **Redline highlighting**: Visual distinction between original (strikethrough) and revised (highlighted) text
- **Checklist rule display**: Full explanation for each redline including:
  - Rule title and severity
  - Edgewater requirement
  - Why it matters
  - Standard language
  - Confidence score
- **Accept/Reject workflow**: Clear buttons for each redline
- **Progress tracking**: Visual indicators for accepted, rejected, and pending redlines
- **Navigation**: Easy prev/next between redlines

### 💾 Export
- Download button (enabled when all redlines reviewed)
- Exports Word document with only accepted changes
- Original filename preserved with "_reviewed" suffix

## Setup

### 1. Install Dependencies

```bash
npm install
# or
yarn install
```

### 2. Configure Backend URL

The frontend is configured to proxy API requests to `http://localhost:8000`.

If your backend runs on a different port, update `next.config.mjs`:

```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://YOUR_BACKEND_URL/api/:path*',
    },
  ];
}
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx                    # Upload page
│   ├── review/[jobId]/page.tsx     # Review interface
│   ├── layout.tsx                  # Root layout
│   └── globals.css                 # Global styles
├── components/
│   └── RedlineReviewer.tsx         # Main review component
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.mjs
```

## Components

### RedlineReviewer

Main component that displays the split-pane review interface.

**Props:**
```typescript
interface Props {
  redlines: Redline[];
  onDecisionChange: (redlineId: string, decision: 'accept' | 'reject') => void;
}
```

**Features:**
- Highlights selected redline
- Displays full checklist rule explanation
- Accept/reject buttons with visual feedback
- Navigation between redlines
- Auto-saves decisions to backend

### Redline Type

```typescript
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
```

## API Integration

The frontend communicates with the backend via these endpoints:

### Upload Document
```typescript
POST /api/upload
Content-Type: multipart/form-data

Response:
{
  job_id: string,
  filename: string,
  status: string
}
```

### Get Job Status
```typescript
GET /api/jobs/{jobId}/status

Response:
{
  job_id: string,
  status: string,
  progress: number,
  redlines: Redline[],
  total_redlines: number
}
```

### Server-Sent Events (Real-time Updates)
```typescript
GET /api/jobs/{jobId}/events

Stream format: text/event-stream
```

### Submit Decisions
```typescript
POST /api/jobs/{jobId}/decisions
Content-Type: application/json

Body:
{
  decisions: [
    { redline_id: string, decision: 'accept' | 'reject' }
  ]
}
```

### Download Document
```typescript
GET /api/jobs/{jobId}/download?final=true

Response: application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

## Styling

Uses Tailwind CSS for styling:
- Responsive design
- Color-coded severity levels:
  - **Critical**: Red
  - **High**: Orange
  - **Moderate**: Yellow
  - **Low**: Blue

## User Experience Flow

1. **Upload**: User drops/selects .docx file
2. **Processing**: Loading screen while backend analyzes
3. **Review**:
   - Left pane: Document with numbered redlines
   - Right pane: Checklist rule for selected redline
   - User clicks ✓ (accept) or ✗ (reject) for each
4. **Navigate**: Use prev/next or click redlines to navigate
5. **Download**: Once all reviewed, download final document

## Environment Variables

No environment variables required. Backend URL is configured in `next.config.mjs`.

## Development Tips

### Hot Reload
Next.js supports hot reload. Changes to components will reflect immediately.

### Type Safety
TypeScript ensures type safety for redline data structures.

### Debugging API Calls
Open browser DevTools Network tab to inspect API requests.

### Testing SSE
Server-sent events can be monitored in Network tab (filter by "events").

## Common Issues

### "API request failed"
- Check backend is running on http://localhost:8000
- Verify `next.config.mjs` proxy configuration

### "Upload not working"
- Check file is .docx format
- Verify backend accepts multipart/form-data

### "Redlines not displaying"
- Check browser console for errors
- Verify API response structure matches `Redline` type

### "Download button disabled"
- Ensure all redlines have a decision (accept or reject)
- Check pending count in header

## Deployment

### Vercel (Recommended)
```bash
npm run build
vercel deploy
```

### Docker
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Configuration
Set backend URL in production:
```bash
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

Update `next.config.mjs` to use environment variable.

## Performance

- Server-side rendering for fast initial load
- Client-side navigation between redlines
- Lazy loading of redline details
- Optimized re-renders with React hooks

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

- [ ] Bulk accept/reject by severity
- [ ] Search/filter redlines
- [ ] Export decisions to PDF report
- [ ] Collaborative review (multiple users)
- [ ] Undo/redo functionality
- [ ] Keyboard shortcuts
- [ ] Dark mode

---

**Version**: 1.0.0
**Last Updated**: 2025-10-05
