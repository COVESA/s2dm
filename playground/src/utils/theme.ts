export type Theme = "light" | "dark" | "system";

export const LIGHT_ICON_CLASS_NAME = "text-amber-500";

/**
 * Tells whether a theme shows the dark look.
 *
 * @param theme The chosen theme.
 * @param isDeviceDark Whether the device prefers a dark look.
 * @returns True for the dark theme. The system theme follows the device.
 */
export function isDarkTheme(theme: Theme, isDeviceDark: boolean): boolean {
	if (theme === "system") {
		return isDeviceDark;
	}

	return theme === "dark";
}

/**
 * Gives the color of a theme's icon. A theme with the light look has an amber
 * icon. A theme with the dark look keeps the default icon color.
 *
 * @param theme The theme of the icon.
 * @param isDeviceDark Whether the device prefers a dark look.
 * @returns The color class, or undefined for the default color.
 */
export function getIconClassName(
	theme: Theme,
	isDeviceDark: boolean,
): string | undefined {
	const isDark = isDarkTheme(theme, isDeviceDark);
	if (isDark) {
		return undefined;
	}

	return LIGHT_ICON_CLASS_NAME;
}
