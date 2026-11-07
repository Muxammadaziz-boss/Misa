// Misa AI — Central Canonical Version Definition (Frontend Single Source of Truth)
// Barcha UI komponentlari, logotiplar va modallar versiyani ushbu yagona manbadan oladi.

export const APP_VERSION = "9.4.0";
export const APP_VERSION_NAME = "v9.4";
export const APP_NAME = "Misa AI";
export const APP_BUILD_DATE = "2026-11-06";

export interface AppVersionInfo {
  version: string;
  versionName: string;
  appName: string;
}

export function getAppVersion(): string {
  return APP_VERSION;
}

export function getAppVersionName(): string {
  return APP_VERSION_NAME;
}
