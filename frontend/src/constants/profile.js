/**
 * Single source of truth for the structured candidate profile.
 * Mirrors backend/app/models/profile.py - keep both in sync.
 *
 * The review form is generated from PROFILE_SECTIONS, so adding a new
 * requirement area later means adding one entry here.
 */

export const EMPTY_PROFILE = {
  name: '',
  email: '',
  phone: '',
  skills: [],
  technologies: [],
  work_experience: [],
  projects: [],
  education: [],
  ai_experience: [],
  development_experience: [],
  tools_platforms: [],
  achievements: [],
}

const WORK_EXPERIENCE_FIELDS = [
  { key: 'title', label: 'Job title', placeholder: 'Senior Software Engineer' },
  { key: 'company', label: 'Company', placeholder: 'Nimbus Labs' },
  { key: 'location', label: 'Location', placeholder: 'Remote' },
  { key: 'start_date', label: 'Start', placeholder: '2021' },
  { key: 'end_date', label: 'End', placeholder: 'Present' },
  { key: 'description', label: 'Description', type: 'textarea' },
  { key: 'technologies', label: 'Technologies used', type: 'list' },
]

const PROJECT_FIELDS = [
  { key: 'name', label: 'Project name', placeholder: 'QuantumHire' },
  { key: 'link', label: 'Link', placeholder: 'https://github.com/...' },
  { key: 'description', label: 'Description', type: 'textarea' },
  { key: 'technologies', label: 'Technologies', type: 'list' },
]

const EDUCATION_FIELDS = [
  { key: 'institution', label: 'Institution', placeholder: 'IIT Madras' },
  { key: 'degree', label: 'Degree', placeholder: 'B.Tech' },
  { key: 'field_of_study', label: 'Field of study', placeholder: 'Computer Science' },
  { key: 'start_date', label: 'Start', placeholder: '2015' },
  { key: 'end_date', label: 'End', placeholder: '2019' },
]

const workEntry = () => ({
  company: '',
  title: '',
  location: '',
  start_date: '',
  end_date: '',
  description: '',
  technologies: [],
})
const projectEntry = () => ({ name: '', description: '', technologies: [], link: '' })
const educationEntry = () => ({
  institution: '',
  degree: '',
  field_of_study: '',
  start_date: '',
  end_date: '',
})

export const PROFILE_SECTIONS = [
  {
    key: 'basic',
    title: 'Basic Information',
    type: 'basic',
    fields: [
      { key: 'name', label: 'Full name', placeholder: 'Aarav Sharma' },
      { key: 'email', label: 'Email', placeholder: 'aarav@example.com' },
      { key: 'phone', label: 'Phone', placeholder: '+91 98765 43210' },
    ],
  },
  { key: 'skills', title: 'Skills', type: 'list', field: 'skills', placeholder: 'Add a skill' },
  {
    key: 'technologies',
    title: 'Technologies',
    type: 'list',
    field: 'technologies',
    placeholder: 'Add a technology',
  },
  {
    key: 'work_experience',
    title: 'Work Experience',
    type: 'objectList',
    field: 'work_experience',
    itemFields: WORK_EXPERIENCE_FIELDS,
    blank: workEntry,
    addLabel: 'Add work experience',
  },
  {
    key: 'projects',
    title: 'Projects',
    type: 'objectList',
    field: 'projects',
    itemFields: PROJECT_FIELDS,
    blank: projectEntry,
    addLabel: 'Add project',
  },
  {
    key: 'education',
    title: 'Education',
    type: 'objectList',
    field: 'education',
    itemFields: EDUCATION_FIELDS,
    blank: educationEntry,
    addLabel: 'Add education',
  },
  {
    key: 'ai_experience',
    title: 'AI Experience',
    type: 'list',
    field: 'ai_experience',
    placeholder: 'Add an AI/LLM statement',
  },
  {
    key: 'development_experience',
    title: 'Development Experience',
    type: 'list',
    field: 'development_experience',
    placeholder: 'Add a development statement',
  },
  {
    key: 'tools_platforms',
    title: 'Tools & Platforms',
    type: 'list',
    field: 'tools_platforms',
    placeholder: 'Add a tool or platform',
  },
  {
    key: 'achievements',
    title: 'Achievements',
    type: 'list',
    field: 'achievements',
    placeholder: 'Add an achievement',
  },
]

/** Normalise any stored/partial profile into the full editable shape. */
export const normalizeProfile = (profile) => {
  const source = profile ?? {}
  const asList = (value) => (Array.isArray(value) ? value.filter(Boolean) : [])

  return {
    ...EMPTY_PROFILE,
    ...source,
    name: source.name ?? '',
    email: source.email ?? '',
    phone: source.phone ?? '',
    skills: asList(source.skills),
    technologies: asList(source.technologies),
    ai_experience: asList(source.ai_experience),
    development_experience: asList(source.development_experience),
    tools_platforms: asList(source.tools_platforms),
    achievements: asList(source.achievements),
    work_experience: Array.isArray(source.work_experience)
      ? source.work_experience.map((entry) => ({ ...workEntry(), ...entry }))
      : [],
    projects: Array.isArray(source.projects)
      ? source.projects.map((entry) => ({ ...projectEntry(), ...entry }))
      : [],
    education: Array.isArray(source.education)
      ? source.education.map((entry) => ({ ...educationEntry(), ...entry }))
      : [],
  }
}

/**
 * Build the editable form state for a candidate.
 * Prefers the machine-extracted profile, then falls back to the top-level
 * candidate fields (for manually created candidates).
 */
export const profileFromCandidate = (candidate) => {
  if (!candidate) return { ...EMPTY_PROFILE }

  if (candidate.extracted_profile) {
    return normalizeProfile(candidate.extracted_profile)
  }

  return normalizeProfile({
    name: candidate.name,
    email: candidate.email,
    phone: candidate.phone,
    skills: candidate.skills,
  })
}
