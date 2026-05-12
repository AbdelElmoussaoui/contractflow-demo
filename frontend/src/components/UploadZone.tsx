import { useRef, useState } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { cn } from '../lib/utils'
import { api } from '../lib/api'
import { Spinner } from './ui/Spinner'

export function UploadZone() {
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const upload = useMutation({
    mutationFn: (file: File) => api.contracts.upload(file),
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      navigate(`/contracts/${contract.id}`)
    },
    onError: (err: Error) => setError(err.message),
  })

  function handleFile(file: File) {
    setError(null)
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Seuls les fichiers PDF sont acceptés.')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('Le fichier dépasse la limite de 50 Mo.')
      return
    }
    upload.mutate(file)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="w-full">
      <div
        onClick={() => !upload.isPending && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-12',
          'cursor-pointer transition-all duration-200 group',
          dragging
            ? 'border-indigo-500 bg-indigo-50/70 scale-[1.01]'
            : 'border-slate-200 bg-white hover:border-indigo-400 hover:bg-slate-50/80',
          upload.isPending && 'cursor-wait pointer-events-none',
        )}
      >
        {upload.isPending ? (
          <>
            <Spinner className="w-10 h-10 text-indigo-500" />
            <p className="text-sm font-medium text-slate-600">Upload en cours…</p>
          </>
        ) : (
          <>
            <div className={cn(
              'p-4 rounded-2xl transition-colors',
              dragging ? 'bg-indigo-100' : 'bg-slate-100 group-hover:bg-indigo-100',
            )}>
              <Upload className={cn(
                'w-8 h-8 transition-colors',
                dragging ? 'text-indigo-600' : 'text-slate-400 group-hover:text-indigo-600',
              )} />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-slate-700">
                Glissez-déposez votre contrat PDF
              </p>
              <p className="text-xs text-slate-400 mt-1">ou cliquez pour parcourir · max 50 Mo</p>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium
                            group-hover:bg-indigo-700 transition-colors shadow-sm shadow-indigo-200">
              <FileText size={15} />
              Choisir un fichier
            </div>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 text-red-700 text-sm">
          <AlertCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}
    </div>
  )
}
