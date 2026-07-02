{{- define "sia-po.labels" -}}
app.kubernetes.io/part-of: sia-po
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "sia-po.databaseUrl" -}}
postgresql+psycopg://{{ .Values.postgres.user }}:{{ .Values.postgres.password }}@{{ .Release.Name }}-postgres:5432/{{ .Values.postgres.database }}
{{- end }}
