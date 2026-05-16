/**
 * JWT signing / verification (RS256) usando `jose`.
 *
 * O Worker assina com privateKey; o cliente Olivas pode validar
 * offline com publicKey embarcada no binário.
 */

import { importPKCS8, importSPKI, SignJWT, jwtVerify } from 'jose';

const ALG = 'RS256';

export interface LicenseJwtPayload {
  tier: string;
  sub: string;        // customer_id
  exp: number;        // unix
  iat: number;
  machine_id: string;
  license_id: string;
}

export async function signLicenseJwt(
  privateKeyPem: string,
  payload: Omit<LicenseJwtPayload, 'iat'>,
): Promise<string> {
  const key = await importPKCS8(privateKeyPem, ALG);
  const now = Math.floor(Date.now() / 1000);
  return await new SignJWT({
    tier: payload.tier,
    machine_id: payload.machine_id,
    license_id: payload.license_id,
  })
    .setProtectedHeader({ alg: ALG })
    .setSubject(payload.sub)
    .setIssuedAt(now)
    .setExpirationTime(payload.exp)
    .setIssuer('olivas-license-server')
    .setAudience('olivas-power-system-studio')
    .sign(key);
}

export async function verifyLicenseJwt(
  publicKeyPem: string,
  token: string,
): Promise<LicenseJwtPayload | null> {
  try {
    const key = await importSPKI(publicKeyPem, ALG);
    const { payload } = await jwtVerify(token, key, {
      issuer: 'olivas-license-server',
      audience: 'olivas-power-system-studio',
    });
    return {
      tier: String(payload.tier ?? ''),
      sub: String(payload.sub ?? ''),
      exp: Number(payload.exp ?? 0),
      iat: Number(payload.iat ?? 0),
      machine_id: String(payload.machine_id ?? ''),
      license_id: String(payload.license_id ?? ''),
    };
  } catch {
    return null;
  }
}
