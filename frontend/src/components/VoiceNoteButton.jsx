import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { extractDraft, setDraftField } from '../store/interactionsSlice'

/** Browser dictation. Chromium/Edge/Safari expose it prefixed; Firefox does not
 *  ship it at all, which is why the control self-disables rather than failing
 *  on click. */
const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

/** "Summarize from Voice Note (Requires Consent)".
 *
 *  Consent is a hard gate, not a formality: nothing is recorded until the rep
 *  confirms the HCP agreed, and the answer is persisted on the interaction
 *  (`consent_obtained`) so the record carries its own audit trail. Declining
 *  simply leaves the feature unused — the rep can still type.
 */
export default function VoiceNoteButton({ hcp }) {
  const dispatch = useDispatch()
  const extracting = useSelector((s) => s.interactions.extracting)
  const consented = useSelector((s) => s.interactions.draft.consent_obtained)

  const [asking, setAsking] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState(null)
  const recognitionRef = useRef(null)

  // Stop the mic if the rep navigates away mid-dictation.
  useEffect(() => () => recognitionRef.current?.stop(), [])

  const supported = Boolean(SpeechRecognition)

  const startListening = () => {
    setError(null)
    setTranscript('')

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    let finalText = ''
    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const chunk = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText += chunk
        else interim += chunk
      }
      setTranscript((finalText + interim).trim())
    }
    recognition.onerror = (event) => {
      setError(
        event.error === 'not-allowed'
          ? 'Microphone access was blocked. Allow it in your browser to dictate.'
          : `Dictation failed (${event.error}).`,
      )
      setListening(false)
    }
    recognition.onend = () => setListening(false)

    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  const grantConsent = () => {
    dispatch(setDraftField({ field: 'consent_obtained', value: true }))
    setAsking(false)
    startListening()
  }

  const stopAndSummarize = async () => {
    recognitionRef.current?.stop()
    setListening(false)
    const text = transcript.trim()
    if (!text) return
    // Same extraction pipeline the chat and the notes box use — the transcript
    // is just another source of free text.
    await dispatch(extractDraft({ hcpId: hcp?.id, text, consent: true }))
    setTranscript('')
  }

  const discard = () => {
    recognitionRef.current?.stop()
    setListening(false)
    setTranscript('')
  }

  // Speech recognition ends itself after a pause, even with continuous = true.
  // When it does, the dictation is still sitting in `transcript` — so offer to
  // summarize it rather than starting a fresh session that would discard it.
  const pending = !listening && Boolean(transcript.trim())

  const onClick = () => {
    if (listening || pending) return stopAndSummarize()
    if (consented) return startListening()
    setAsking(true)
  }

  if (!supported) {
    return (
      <div className="voice-note">
        <span className="voice-disabled" title="Your browser has no Speech Recognition API">
          🎙 Voice note unavailable in this browser
        </span>
      </div>
    )
  }

  return (
    <div className="voice-note">
      <button
        type="button"
        className={`voice-link ${listening ? 'live' : ''}`}
        onClick={onClick}
        disabled={extracting}
      >
        {listening ? (
          <>
            <span className="rec-dot" /> Stop &amp; summarize
          </>
        ) : pending ? (
          <>✨ Summarize what I heard</>
        ) : (
          <>🎙 Summarize from Voice Note {consented ? '' : '(Requires Consent)'}</>
        )}
      </button>

      {pending && !extracting && (
        <button type="button" className="voice-secondary" onClick={discard}>
          Discard
        </button>
      )}

      {extracting && <span className="voice-status">Summarizing…</span>}

      {asking && (
        <div className="consent-box">
          <div className="consent-title">🔒 Consent required</div>
          <p>
            Before recording, confirm that{' '}
            <b>{hcp?.name || 'the HCP'}</b> has been informed and has agreed to this
            interaction being captured as a voice note. Your answer is stored on the
            interaction record.
          </p>
          <div className="btn-row">
            <button type="button" className="btn sm" onClick={grantConsent}>
              Consent given — start recording
            </button>
            <button type="button" className="btn ghost sm" onClick={() => setAsking(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {(listening || pending) && (
        <div className="transcript-box">
          <div className={`transcript-label ${pending ? 'done' : ''}`}>
            {listening ? (
              <>
                <span className="rec-dot" /> Listening…
              </>
            ) : (
              <>Voice note captured — review, then summarize</>
            )}
          </div>
          <div className="transcript-text">
            {transcript || <span className="muted">Start speaking — your words appear here.</span>}
          </div>
        </div>
      )}

      {error && <div className="voice-error">⚠️ {error}</div>}
    </div>
  )
}
