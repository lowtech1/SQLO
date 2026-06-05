/**
 * SqlHighlighter.jsx
 * Tokenizes and syntax-highlights SQL code.
 * Supports: keywords, functions, strings, numbers, comments, operators, columns/tables.
 * Used inside DecisionCard for Before/After code snippets.
 */

/** @type {Record<string, {regex: RegExp, cls: string}>} */
const TOKEN_RULES = {
  // Block comments first (before other rules)
  blockComment: {
    regex: /(--[^\n]*|--.*$)/g,
    cls: "sql-comment",
  },
  // Single-line comment
  lineComment: {
    regex: /(\/\*[\s\S]*?\*\/)/g,
    cls: "sql-comment",
  },
  // Strings (single-quoted)
  string: {
    regex: /('(?:[^'\\]|\\.)*')/g,
    cls: "sql-string",
  },
  // Double-quoted identifiers
  doubleQuote: {
    regex: /("(?:[^"\\]|\\.)*")/g,
    cls: "sql-table",
  },
  // Numbers
  number: {
    regex: /\b(\d+(?:\.\d+)?)\b/g,
    cls: "sql-number",
  },
  // SQL keywords (uppercase, grouped by priority)
  keyword: {
    regex:
      /\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|OUTER|FULL|CROSS|ON|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|AS|ASC|DESC|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|UNION|INTERSECT|EXCEPT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|SET|VALUES|WITH|RECURSIVE|CASE|WHEN|THEN|ELSE|END|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|INDEX|DEFAULT|CHECK|CONSTRAINT|FOR|INTO|DISTINCT|ALL|OVER|WINDOW|PARTITION|ROWS|RANGE|ROWS|BETWEEN|UNBOUNDED|PRECEDING|FOLLOWING|CURRENT|NOW|COALESCE|CAST|CONVERT|SUM|COUNT|AVG|MIN|MAX|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|FIRST_VALUE|LAST_VALUE|NULLIF|IIF|GREATEST|LEAST|EXTRACT|DATE_TRUNC|GROUPING)\b/gi,
    cls: "sql-keyword",
  },
  // SQL functions
  function: {
    regex:
      /\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|NULLIF|CAST|CONVERT|LOWER|UPPER|TRIM|LTRIM|RTRIM|LENGTH|SUBSTRING|SUBSTR|REPLACE|REVERSE|CHARINDEX|POSITION|CONCAT|SPLIT_PART|JSONB_EXTRACT|CARDINALITY|ARRAY_AGG|STRING_AGG|TO_CHAR|TO_DATE|TO_NUMBER|FLOOR|CEIL|ROUND|ABS|POWER|SQRT|LOG|LN|EXP|SIGN|ROW_NUMBER|RANK|DENSE_RANK|NTILE)\s*(?=\()/gi,
    cls: "sql-function",
  },
  // Comparison operators
  operator: {
    regex: /(>=|<=|:=|<>|!=|=|<|>|\+|-|\*|\/|\|\|)/g,
    cls: "sql-operator",
  },
  // Identifiers (table.column or alias)
  identifier: {
    regex: /([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)/g,
    cls: "sql-identifier",
  },
};

/**
 * Tokenize SQL string into spans with CSS classes.
 * @param {string} sql
 * @returns {Array<{text: string, cls: string}>}
 */
function tokenize(sql) {
  if (!sql) return [{ text: "", cls: "" }];

  // Split by newlines, then tokenize each line
  const lines = sql.split("\n");
  const result = [];

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    if (li > 0) {
      result.push({ text: "\n", cls: "" });
    }

    let remaining = line;
    let pos = 0;

    while (remaining.length > 0) {
      let earliestMatch = null;
      let earliestRule = null;
      let earliestIdx = remaining.length;

      for (const [ruleName, rule] of Object.entries(TOKEN_RULES)) {
        rule.regex.lastIndex = 0;
        const match = rule.regex.exec(remaining);
        if (match && match.index < earliestIdx) {
          earliestIdx = match.index;
          earliestMatch = match[0];
          earliestRule = ruleName;
        }
      }

      if (!earliestMatch) {
        // Plain text — consume one char
        if (remaining[0] !== "\n") {
          result.push({ text: remaining[0], cls: "" });
        }
        remaining = remaining.slice(1);
        pos++;
        continue;
      }

      // Text before match
      const before = remaining.slice(0, earliestIdx);
      if (before) {
        for (const ch of before) {
          if (ch !== "\n") {
            result.push({ text: ch, cls: "" });
          }
        }
      }

      // The match itself — check for duplicate keyword assignment
      const matched = earliestMatch;
      let cls = TOKEN_RULES[earliestRule].cls;

      // Don't double-classify identifiers that are keywords
      if (
        earliestRule === "identifier" &&
        TOKEN_RULES.keyword.regex.test(matched)
      ) {
        TOKEN_RULES.keyword.regex.lastIndex = 0;
        cls = "";
      }

      result.push({ text: matched, cls });
      remaining = remaining.slice(earliestIdx + matched.length);
    }
  }

  return result;
}

/**
 * Simple but effective SQL syntax highlighter.
 * Returns JSX with appropriate CSS class spans.
 * @param {string} sql
 * @param {string} [theme] - 'dark' (default) or 'light'
 */
export function SqlHighlighter({ sql = "", theme = "dark" }) {
  if (!sql) {
    return (
      <span className="text-text-muted italic text-xs">
        (empty)
      </span>
    );
  }

  const tokens = tokenize(sql);
  const isDark = theme === "dark";

  const baseClass = isDark
    ? "text-[#E6EDF3] font-mono text-xs leading-relaxed"
    : "text-gray-900 font-mono text-xs leading-relaxed";

  return (
    <code className={baseClass}>
      {tokens.map((tok, i) => {
        if (!tok.text || tok.text === "\n") {
          return tok.text === "\n" ? (
            <br key={i} />
          ) : null;
        }
        const spanClass = tok.cls
          ? `${tok.cls} font-medium`
          : isDark
          ? "text-[#E6EDF3]"
          : "text-gray-900";
        return (
          <span key={i} className={spanClass}>
            {tok.text}
          </span>
        );
      })}
    </code>
  );
}

/** Build a simple line-numbered code block */
export function CodeBlock({ sql = "", theme = "dark" }) {
  const lines = sql.split("\n");

  return (
    <pre
      className={`
        relative w-full overflow-x-auto rounded-lg p-4
        font-mono text-xs leading-relaxed whitespace-pre
        ${theme === "dark"
          ? "bg-bg-code border border-bg-border text-text-primary"
          : "bg-gray-50 border border-gray-200 text-gray-900"
        }
      `}
    >
      {/* Line numbers */}
      <span
        aria-hidden="true"
        className={`
          absolute left-0 top-0 bottom-0 w-10
          flex flex-col items-end pr-3 pt-4 pb-4
          select-none text-right
          ${theme === "dark" ? "text-text-muted" : "text-gray-400"}
          font-mono text-xs leading-relaxed
          border-r ${theme === "dark" ? "border-bg-border" : "border-gray-200"}
        `}
      >
        {lines.map((_, i) => (
          <span key={i}>{i + 1}</span>
        ))}
      </span>

      {/* Code content with padding for line numbers */}
      <span className="pl-10 block">
        <SqlHighlighter sql={sql} theme={theme} />
      </span>
    </pre>
  );
}

export default SqlHighlighter;
