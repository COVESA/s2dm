type ImportErrorBannerProps = {
	children: React.ReactNode;
};

export function ImportErrorBanner({ children }: ImportErrorBannerProps) {
	return (
		<div className="mx-2 mb-2 p-2 text-sm bg-destructive/10 text-destructive rounded border border-destructive">
			{children}
		</div>
	);
}
