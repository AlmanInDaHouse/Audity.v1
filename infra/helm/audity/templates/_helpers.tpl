{{- define "audity.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "audity.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "audity.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "audity.labels" -}}
app.kubernetes.io/name: {{ include "audity.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $key, $value := .Values.global.commonLabels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end -}}

{{- define "audity.selectorLabels" -}}
app.kubernetes.io/name: {{ include "audity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
