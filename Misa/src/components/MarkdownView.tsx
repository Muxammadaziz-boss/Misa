import React, { useState } from "react";
import { CopyIcon, CheckIcon } from "./icons/Icons";

interface MarkdownViewProps {
  content: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({ content }) => {
  // Parse code blocks vs regular text blocks
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const parts: React.ReactNode[] = [];

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  const renderInlineFormatted = (text: string, keyPrefix: string) => {
    // Process lines and lists
    const lines = text.split("\n");
    return lines.map((line, lineIdx) => {
      const trimmed = line.trim();
      const isBullet = trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ");
      const bulletContent = isBullet ? trimmed.slice(2) : line;

      // Inline code and bold formatting
      // Split by backticks
      const codeSegments = bulletContent.split(/(`[^`]+`)/g);

      const formattedLine = codeSegments.map((segment, segIdx) => {
        if (segment.startsWith("`") && segment.endsWith("`") && segment.length > 2) {
          return (
            <code
              key={`${keyPrefix}-${lineIdx}-${segIdx}`}
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.08)",
                color: "#38BDF8",
                padding: "2px 6px",
                borderRadius: "4px",
                fontSize: "12.5px",
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
              }}
            >
              {segment.slice(1, -1)}
            </code>
          );
        }

        // Bold formatting **text**
        const boldSegments = segment.split(/(\*\*[^*]+\*\*)/g);
        return boldSegments.map((bSeg, bIdx) => {
          if (bSeg.startsWith("**") && bSeg.endsWith("**") && bSeg.length > 4) {
            return (
              <strong key={`${keyPrefix}-${lineIdx}-${segIdx}-${bIdx}`} style={{ color: "#FFFFFF", fontWeight: 600 }}>
                {bSeg.slice(2, -2)}
              </strong>
            );
          }
          return bSeg;
        });
      });

      if (isBullet) {
        return (
          <div
            key={`${keyPrefix}-${lineIdx}`}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
              margin: "3px 0",
              paddingLeft: "4px",
            }}
          >
            <span style={{ color: "#38BDF8", fontSize: "14px", lineHeight: 1.4 }}>•</span>
            <span style={{ flex: 1 }}>{formattedLine}</span>
          </div>
        );
      }

      return (
        <React.Fragment key={`${keyPrefix}-${lineIdx}`}>
          {formattedLine}
          {lineIdx < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  while ((match = codeBlockRegex.exec(content)) !== null) {
    const preText = content.substring(lastIndex, match.index);
    if (preText) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {renderInlineFormatted(preText, `pre-${lastIndex}`)}
        </span>
      );
    }

    const language = match[1] || "code";
    const code = match[2];
    const blockIndex = match.index;

    parts.push(
      <CodeBlock key={`code-${blockIndex}`} language={language} code={code} />
    );

    lastIndex = match.index + match[0].length;
  }

  const remaining = content.substring(lastIndex);
  if (remaining) {
    parts.push(
      <span key={`text-${lastIndex}`}>
        {renderInlineFormatted(remaining, `post-${lastIndex}`)}
      </span>
    );
  }

  return (
    <div
      className="markdown-content selectable-text"
      style={{
        wordBreak: "break-word",
        userSelect: "text",
        WebkitUserSelect: "text",
        cursor: "text",
      }}
    >
      {parts}
    </div>
  );
};

interface CodeBlockProps {
  language: string;
  code: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div
      style={{
        margin: "10px 0",
        borderRadius: "10px",
        backgroundColor: "#070B14",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 12px",
          backgroundColor: "rgba(255, 255, 255, 0.03)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
          fontSize: "11px",
          color: "var(--text-muted, #94A3B8)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        <span>{language}</span>
        <button
          onClick={handleCopy}
          title="Kodni nusxalash"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            background: "transparent",
            border: "none",
            color: copied ? "#10B981" : "var(--text-muted, #94A3B8)",
            cursor: "pointer",
            fontSize: "11px",
            padding: "2px 6px",
            borderRadius: "4px",
            transition: "all 0.15s ease",
          }}
        >
          {copied ? <CheckIcon size={12} color="#10B981" /> : <CopyIcon size={12} color="currentColor" />}
          <span>{copied ? "Nusxalandi" : "Nusxa"}</span>
        </button>
      </div>

      <pre
        className="selectable-text"
        style={{
          margin: 0,
          padding: "12px",
          overflowX: "auto",
          fontSize: "12.5px",
          fontFamily: 'Consolas, Monaco, "Courier New", monospace',
          color: "#E2E8F0",
          lineHeight: 1.5,
          userSelect: "text",
          WebkitUserSelect: "text",
          cursor: "text",
        }}
      >
        <code style={{ userSelect: "text", WebkitUserSelect: "text" }}>{code.trimEnd()}</code>
      </pre>
    </div>
  );
};
