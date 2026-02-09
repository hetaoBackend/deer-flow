/**
 * Citation data structure representing a source reference
 */
export interface Citation {
  id: string;
  title: string;
  url: string;
  snippet: string;
}

/**
 * Result of parsing citations from content
 */
export interface ParseCitationsResult {
  citations: Citation[];
  cleanContent: string;
}

/**
 * Parse citations block from message content.
 *
 * The citations block format:
 * <citations>
 * {"id": "cite-1", "title": "Page Title", "url": "https://example.com", "snippet": "Description"}
 * {"id": "cite-2", "title": "Another Page", "url": "https://example2.com", "snippet": "Description"}
 * </citations>
 *
 * @param content - The raw message content that may contain a citations block
 * @returns Object containing parsed citations array and content with citations block removed
 */
export function parseCitations(content: string): ParseCitationsResult {
  if (!content) {
    return { citations: [], cleanContent: content };
  }

  // Match ALL citations blocks anywhere in content (not just at the start)
  const citationsRegex = /<citations>([\s\S]*?)<\/citations>/g;
  const citations: Citation[] = [];
  const seenUrls = new Set<string>(); // Deduplicate by URL
  let cleanContent = content;

  let match;
  while ((match = citationsRegex.exec(content)) !== null) {
    const citationsBlock = match[1] ?? "";

    // Parse each line as JSON
    const lines = citationsBlock.split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed?.startsWith("{")) {
        try {
          const citation = JSON.parse(trimmed) as Citation;
          // Validate required fields and deduplicate
          if (citation.id && citation.url && !seenUrls.has(citation.url)) {
            seenUrls.add(citation.url);
            citations.push({
              id: citation.id,
              title: citation.title || "",
              url: citation.url,
              snippet: citation.snippet || "",
            });
          }
        } catch {
          // Skip invalid JSON lines - this can happen during streaming
        }
      }
    }
  }

  // Remove ALL citations blocks from content (both complete and incomplete)
  cleanContent = content.replace(/<citations>[\s\S]*?<\/citations>/g, "").trim();
  
  // Also remove incomplete citations blocks (during streaming)
  // Match <citations> without closing tag or <citations> followed by anything until end of string
  if (cleanContent.includes("<citations>")) {
    cleanContent = cleanContent.replace(/<citations>[\s\S]*$/g, "").trim();
  }

  // Convert [cite-N] references to markdown links
  // Example: [cite-1] -> [Title](url)
  if (citations.length > 0) {
    // Build a map from citation id to citation object
    const idMap = new Map<string, Citation>();
    for (const citation of citations) {
      idMap.set(citation.id, citation);
    }

    // Replace all [cite-N] patterns with markdown links
    cleanContent = cleanContent.replace(/\[cite-(\d+)\]/g, (match, num) => {
      const citeId = `cite-${num}`;
      const citation = idMap.get(citeId);
      if (citation) {
        // Use title if available, otherwise use domain
        const linkText = citation.title || extractDomainFromUrl(citation.url);
        return `[${linkText}](${citation.url})`;
      }
      // If citation not found, keep the original text
      return match;
    });
  }

  return { citations, cleanContent };
}

/**
 * Build a map from URL to Citation for quick lookup
 *
 * @param citations - Array of citations
 * @returns Map with URL as key and Citation as value
 */
export function buildCitationMap(
  citations: Citation[],
): Map<string, Citation> {
  const map = new Map<string, Citation>();
  for (const citation of citations) {
    map.set(citation.url, citation);
  }
  return map;
}

/**
 * Extract the domain name from a URL for display
 *
 * @param url - Full URL string
 * @returns Domain name or the original URL if parsing fails
 */
export function extractDomainFromUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    // Remove 'www.' prefix if present
    return urlObj.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/**
 * Check if content is still receiving the citations block (streaming)
 * This helps determine if we should wait before parsing
 *
 * @param content - The current content being streamed
 * @returns true if citations block appears to be incomplete
 */
export function isCitationsBlockIncomplete(content: string): boolean {
  if (!content) {
    return false;
  }

  // Check if we have an opening tag but no closing tag
  const hasOpenTag = content.includes("<citations>");
  const hasCloseTag = content.includes("</citations>");

  return hasOpenTag && !hasCloseTag;
}

/**
 * Remove ALL citations from content, including:
 * - <citations> blocks
 * - [cite-N] references
 * - Citation markdown links that were converted from [cite-N]
 * 
 * This is used for copy/download operations where we want clean content without any references.
 *
 * @param content - The raw content that may contain citations
 * @returns Content with all citations completely removed
 */
export function removeAllCitations(content: string): string {
  if (!content) {
    return content;
  }

  let result = content;

  // Step 1: Remove all <citations> blocks (complete and incomplete)
  result = result.replace(/<citations>[\s\S]*?<\/citations>/g, "");
  result = result.replace(/<citations>[\s\S]*$/g, "");

  // Step 2: Remove all [cite-N] references
  result = result.replace(/\[cite-\d+\]/g, "");

  // Step 3: Parse to find citation URLs and remove those specific links
  const parsed = parseCitations(content);
  const citationUrls = new Set(parsed.citations.map(c => c.url));
  
  // Remove markdown links that point to citation URLs
  // Pattern: [text](url)
  result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
    // If this URL is a citation, remove the entire link
    if (citationUrls.has(url)) {
      return "";
    }
    // Keep non-citation links
    return match;
  });

  // Step 4: Clean up extra whitespace and newlines
  result = result
    .replace(/\n{3,}/g, "\n\n") // Replace 3+ newlines with 2
    .trim();

  return result;
}
