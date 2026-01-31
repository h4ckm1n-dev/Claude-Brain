# Test Document for MD to PDF Conversion

This is a test document to demonstrate the markdown to PDF conversion with proper formatting preservation.

## Features Demo

### Text Formatting

This paragraph demonstrates **bold text**, *italic text*, and ***bold italic text***. You can also use inline `code snippets` within paragraphs.

### Lists

Unordered list:
- First item
- Second item
  - Nested item 1
  - Nested item 2
- Third item

Ordered list:
1. First step
2. Second step
3. Third step

### Code Blocks

```python
def greet(name):
    """A simple greeting function."""
    return f"Hello, {name}!"

# Usage
message = greet("World")
print(message)
```

```javascript
// JavaScript example
const fibonacci = (n) => {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
};

console.log(fibonacci(10));
```

### Tables

| Feature | Status | Priority |
|---------|--------|----------|
| PDF Export | ✓ Complete | High |
| Custom CSS | ✓ Complete | High |
| Syntax Highlighting | ✓ Complete | Medium |
| Page Numbers | ✓ Complete | Low |

### Blockquotes

> "The best way to predict the future is to invent it."
>
> — Alan Kay

### Links

Check out the [documentation](https://github.com) for more information.

---

## Advanced Features

### Mathematical Notation

While WeasyPrint doesn't natively support LaTeX, you can use Unicode symbols:
- ∑, ∫, ∂, √, π, ∞
- α, β, γ, δ, ε

### Horizontal Rules

Above this text is a horizontal rule created with `---`.

---

### Long Paragraph Test

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

## Conclusion

This test document demonstrates various markdown features that are properly converted to PDF with preserved formatting and layout.

**Test Date**: 2025-11-06
**Version**: 1.0
