export type User = {
  id: string
  email: string
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  user: User
}
