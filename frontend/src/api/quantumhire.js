import apiClient, { endpoints } from '../api/client.js'

/** Normalise a FastAPI role document for the UI. */
const normalizeRole = (role) => ({
  ...role,
  requirements: Array.isArray(role?.requirements) ? role.requirements : [],
})

/** Normalise a FastAPI candidate document for the UI. */
const normalizeCandidate = (candidate) => ({
  ...candidate,
  skills: Array.isArray(candidate?.skills) ? candidate.skills : [],
  extracted_profile: candidate?.extracted_profile ?? null,
  evaluation: candidate?.evaluation ?? null,
  skill_test: candidate?.skill_test ?? null,
  has_resume: Boolean(candidate?.has_resume),
  profile_reviewed: Boolean(candidate?.profile_reviewed),
  extraction_warnings: Array.isArray(candidate?.extraction_warnings)
    ? candidate.extraction_warnings
    : [],
})

export const getHealth = async () => {
  const { data } = await apiClient.get(endpoints.health)
  return data
}

export const getDashboardSummary = async () => {
  const { data } = await apiClient.get(endpoints.dashboardSummary)
  return data
}

export const getRoles = async () => {
  const { data } = await apiClient.get(endpoints.roles)
  return (data ?? []).map(normalizeRole)
}

export const getRole = async (roleId) => {
  const { data } = await apiClient.get(`${endpoints.roles}/${roleId}`)
  return normalizeRole(data)
}

/**
 * Create a job role (POST /api/roles). The backend validates the payload,
 * derives a unique slug and persists it to MongoDB before responding.
 */
export const createRole = async (payload) => {
  const { data } = await apiClient.post(endpoints.roles, payload)
  return normalizeRole(data)
}

export const getCandidates = async (params = {}) => {
  const { data } = await apiClient.get(endpoints.candidates, { params })
  return (data ?? []).map(normalizeCandidate)
}

export const getCandidate = async (candidateId) => {
  const { data } = await apiClient.get(`${endpoints.candidates}/${candidateId}`)
  return normalizeCandidate(data)
}

/**
 * Upload a PDF resume: the backend validates it, extracts the text, structures a
 * candidate profile and creates the candidate. `onUploadProgress` drives the
 * browser-side upload bar; extraction happens server-side after the bytes land.
 */
export const uploadResume = async (file, { roleId, stage, source } = {}, options = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  if (roleId) formData.append('role_id', roleId)
  if (stage) formData.append('stage', stage)
  if (source) formData.append('source', source)

  const { data } = await apiClient.post(endpoints.resumeUpload, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
    onUploadProgress: options.onUploadProgress,
  })

  return data
}

/** Save the recruiter-reviewed profile and approve it as candidate evidence. */
export const updateCandidateProfile = async (candidateId, profile) => {
  const { data } = await apiClient.put(`${endpoints.candidates}/${candidateId}/profile`, profile)
  return normalizeCandidate(data)
}

/**
 * Recruiter stage change: PATCH /api/candidates/{id}/stage?stage=...
 * Persists to MongoDB, records a stage_changed workflow event and refreshes
 * the dashboard counters. The API rejects unknown stages.
 */
export const updateCandidateStage = async (candidateId, stage) => {
  const { data } = await apiClient.patch(
    `${endpoints.candidates}/${candidateId}/stage`,
    null,
    { params: { stage } },
  )
  return normalizeCandidate(data)
}

// --- auth -------------------------------------------------------------------

/** Exchange credentials for a JWT; the caller stores the token. */
export const login = async ({ email, password }) => {
  const { data } = await apiClient.post(endpoints.login, { email, password })
  return data
}

export const getCurrentUser = async () => {
  const { data } = await apiClient.get(endpoints.me)
  return data
}

// --- evaluation (milestone 3) ----------------------------------------------

/** Run the AI evaluation; requires an approved profile (409 otherwise). */
export const runEvaluation = async (candidateId) => {
  const { data } = await apiClient.post(`${endpoints.candidates}/${candidateId}/evaluate`)
  return data
}

export const getEvaluation = async (candidateId) => {
  const { data } = await apiClient.get(`${endpoints.candidates}/${candidateId}/evaluation`)
  return data
}

export const updateEvaluation = async (candidateId, changes) => {
  const { data } = await apiClient.put(
    `${endpoints.candidates}/${candidateId}/evaluation`,
    changes,
  )
  return data
}

export const approveEvaluation = async (candidateId) => {
  const { data } = await apiClient.post(`${endpoints.candidates}/${candidateId}/evaluation/approve`)
  return data
}

// --- skill test (milestone 3) ----------------------------------------------

export const generateSkillTest = async (candidateId) => {
  const { data } = await apiClient.post(`${endpoints.candidates}/${candidateId}/generate-test`)
  return data
}

export const getSkillTest = async (candidateId) => {
  const { data } = await apiClient.get(`${endpoints.candidates}/${candidateId}/skill-test`)
  return data
}

export const updateSkillTest = async (candidateId, changes) => {
  const { data } = await apiClient.put(`${endpoints.candidates}/${candidateId}/skill-test`, changes)
  return data
}

export const approveSkillTest = async (candidateId) => {
  const { data } = await apiClient.post(`${endpoints.candidates}/${candidateId}/skill-test/approve`)
  return data
}

// --- activity + knowledge ---------------------------------------------------

/** Workflow event timeline (newest first). */
export const getCandidateEvents = async (candidateId) => {
  const { data } = await apiClient.get(`${endpoints.candidates}/${candidateId}/events`)
  return data ?? []
}

/** Keyword search over the internal knowledge base (RAG). */
export const searchKnowledge = async (q, topK = 4) => {
  const { data } = await apiClient.get(endpoints.knowledge, { params: { q, top_k: topK } })
  return data
}

/** The allowlisted agent tool catalog. */
export const getAgentTools = async () => {
  const { data } = await apiClient.get(endpoints.agentTools)
  return data ?? []
}
