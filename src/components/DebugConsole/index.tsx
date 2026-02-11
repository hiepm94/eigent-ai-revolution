// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========

import { useEffect, useRef, useState } from 'react';

interface LogEntry {
  timestamp: string;
  level: 'log' | 'error' | 'warn' | 'info' | 'debug';
  message: string;
}

/**
 * Debug Console Component
 *
 * Displays console logs in a floating panel within the application.
 * Only shows logs containing the specified filter keywords.
 */
export default function DebugConsole() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const maxLogs = 100;

  // Filter keywords that should be logged
  const filterKeywords = [
    '[InputBox]',
    '[ChatBox]',
    '[handleSend]',
    '[Multi-turn]',
  ];

  useEffect(() => {
    // Override console.log to capture logs
    const originalLog = console.log;
    const originalError = console.error;

    const captureLog = (level: 'log' | 'error', args: any[]) => {
      try {
        const message = args
          .map((arg) => {
            if (typeof arg === 'object') {
              try {
                return JSON.stringify(arg, null, 2);
              } catch {
                return String(arg);
              }
            }
            return String(arg);
          })
          .join(' ');

        // Only capture logs with our filter keywords
        const shouldCapture = filterKeywords.some((keyword) =>
          message.includes(keyword)
        );

        if (shouldCapture) {
          setLogs((prevLogs) => {
            const newLogs = [
              ...prevLogs,
              {
                timestamp: new Date().toLocaleTimeString(),
                level,
                message,
              },
            ];
            return newLogs.slice(-maxLogs);
          });
        }
      } catch (e) {
        // Silently fail if there's any issue capturing
      }
    };

    console.log = (...args: any[]) => {
      originalLog(...args);
      captureLog('log', args);
    };

    console.error = (...args: any[]) => {
      originalError(...args);
      captureLog('error', args);
    };

    return () => {
      console.log = originalLog;
      console.error = originalError;
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const filteredLogs = filter
    ? logs.filter((log) =>
        log.message.toLowerCase().includes(filter.toLowerCase())
      )
    : logs;

  return (
    <>
      {/* Button - Fixed position, high z-index */}
      <div
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 9999,
        }}
      >
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            width: '50px',
            height: '50px',
            borderRadius: '8px',
            backgroundColor: '#1e293b',
            border: '2px solid #22c55e',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#22c55e',
          }}
          title="Toggle Debug Console"
        >
          ◀►
        </button>
      </div>

      {/* Console Panel */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            zIndex: 9998,
            width: '500px',
            maxHeight: '400px',
            backgroundColor: '#0f172a',
            border: '2px solid #22c55e',
            borderRadius: '8px',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
            fontFamily: 'monospace',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px',
              borderBottom: '2px solid #22c55e',
              backgroundColor: '#1e293b',
            }}
          >
            <span
              style={{ color: '#22c55e', fontWeight: 'bold', fontSize: '14px' }}
            >
              🔍 Debug Console
            </span>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: 'none',
                border: 'none',
                color: '#22c55e',
                cursor: 'pointer',
                fontSize: '18px',
              }}
            >
              ✕
            </button>
          </div>

          {/* Filter Input */}
          <input
            type="text"
            placeholder="Filter logs..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              margin: '8px',
              padding: '8px',
              fontSize: '12px',
              backgroundColor: '#1e293b',
              border: '1px solid #22c55e',
              borderRadius: '4px',
              color: '#e2e8f0',
            }}
          />

          {/* Logs */}
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '8px',
              fontSize: '12px',
              lineHeight: '1.5',
              color: '#e2e8f0',
            }}
          >
            {filteredLogs.length === 0 ? (
              <div
                style={{
                  color: '#64748b',
                  textAlign: 'center',
                  paddingTop: '20px',
                }}
              >
                {logs.length === 0
                  ? '⏳ No logs yet... (Try sending a message)'
                  : '❌ No logs matching filter'}
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  style={{
                    marginBottom: '4px',
                    color: log.level === 'error' ? '#ef4444' : '#22c55e',
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  <span style={{ color: '#64748b' }}>[{log.timestamp}]</span>{' '}
                  {log.message}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div
            style={{
              padding: '8px',
              borderTop: '1px solid #22c55e',
              backgroundColor: '#1e293b',
              color: '#64748b',
              fontSize: '11px',
            }}
          >
            {filteredLogs.length} / {logs.length} logs
          </div>
        </div>
      )}
    </>
  );
}
