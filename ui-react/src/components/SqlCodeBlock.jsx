/**
 * SqlCodeBlock.jsx
 * SQL code display using react-syntax-highlighter (vscDarkPlus theme).
 * Background forced to #0D1117 regardless of theme selection.
 *
 * @param {string} code      - SQL string to display
 * @param {string} [className] - Optional wrapper class
 */

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const customStyle = {
  ...vscDarkPlus,
  'pre[class*="language-"]': {
    ...vscDarkPlus['pre[class*="language-"]'],
    background: "#0D1117",
    margin: 0,
    padding: "1rem",
    borderRadius: 0,
    fontSize: "12px",
    lineHeight: "1.6",
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
  },
  'code[class*="language-"]': {
    ...vscDarkPlus['code[class*="language-"]'],
    background: "#0D1117",
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: "12px",
  },
};

export function SqlCodeBlock({ code = "", className = "" }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <SyntaxHighlighter
        language="sql"
        style={customStyle}
        customStyle={{
          background: "#0D1117",
          margin: 0,
          padding: "1rem",
          borderRadius: 0,
          fontSize: "12px",
          lineHeight: "1.6",
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          wordBreak: "break-all",
          whiteSpace: "pre-wrap",
        }}
        codeTagProps={{
          style: {
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            background: "#0D1117",
          },
        }}
        showLineNumbers
        lineNumberStyle={{
          color: "#484F58",
          minWidth: "2.5em",
          paddingRight: "1em",
          userSelect: "none",
          fontSize: "11px",
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

export default SqlCodeBlock;
