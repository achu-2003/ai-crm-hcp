import { useState } from 'react'

/** A list-of-strings field rendered as removable chips.
 *
 *  Backs Attendees, Materials Shared and Samples Distributed — all three are
 *  "type a thing, press Enter, get a chip" and differ only in their labels and
 *  suggestions. `suggestions` are one-tap adds (e.g. the HCP's preferred
 *  products, the standard leave-behinds). */
export default function ChipInput({
  value = [],
  onChange,
  placeholder,
  addLabel = '+ Add',
  suggestions = [],
  highlight = false,
}) {
  const [text, setText] = useState('')

  const add = (raw) => {
    const item = raw.trim()
    if (!item) return
    // Case-insensitive dedupe, first spelling wins.
    if (value.some((v) => v.toLowerCase() === item.toLowerCase())) {
      setText('')
      return
    }
    onChange([...value, item])
    setText('')
  }

  const remove = (item) => onChange(value.filter((v) => v !== item))

  const onKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add(text)
    } else if (e.key === 'Backspace' && !text && value.length) {
      remove(value[value.length - 1])
    }
  }

  const unused = suggestions.filter(
    (s) => !value.some((v) => v.toLowerCase() === s.toLowerCase()),
  )

  return (
    <div className={`chip-input ${highlight ? 'ai-filled' : ''}`}>
      {value.length > 0 && (
        <div className="chip-list">
          {value.map((item) => (
            <span className="tag" key={item}>
              {item}
              <button
                type="button"
                className="tag-x"
                onClick={() => remove(item)}
                aria-label={`Remove ${item}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="chip-row-input">
        <input
          type="text"
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="button" className="btn ghost sm" onClick={() => add(text)} disabled={!text.trim()}>
          {addLabel}
        </button>
      </div>

      {unused.length > 0 && (
        <div className="chip-suggestions">
          {unused.map((s) => (
            <button type="button" key={s} className="suggest-chip" onClick={() => add(s)}>
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
