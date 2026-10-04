{{/*
Nazwa bazowa wszystkich obiektów. Wyprowadzona z nazwy wydania, żeby dwa wydania tego
samego charta w jednym klastrze nie deptały sobie po nazwach.
*/}}
{{- define "app.name" -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{/*
Etykiety wspólne dla wszystkich obiektów. `app.kubernetes.io/*` to nazwy uzgodnione
w całym ekosystemie — po nich filtruje k9s, kubectl i większość narzędzi.
*/}}
{{- define "app.labels" -}}
app.kubernetes.io/name: {{ include "app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Pełna nazwa obrazu. Tag jest wymagany i celowo nie ma wartości domyślnej: brak tagu ma
zatrzymać wdrożenie z czytelnym błędem, a nie po cichu wziąć „latest".
*/}}
{{- define "app.image" -}}
{{- $tag := required "image.tag jest wymagany — ustawia go Argo Application w repo platformy" .Values.image.tag -}}
{{ .Values.image.registry }}/{{ .component }}:{{ $tag }}
{{- end -}}
