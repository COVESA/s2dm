import { ExternalLink } from "lucide-react";
import { TextEditor } from "@/components/TextEditor";
import { Checkbox } from "@/components/ui/checkbox";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { FormLabel } from "@/components/ui/form-label";
import { Input } from "@/components/ui/input";
import {
	selectExporterByEndpoint,
	updatePropertyValue,
} from "@/store/capabilities/capabilitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type ExportConfigProps = {
	selectedExporterEndpoint: string;
};

export function ExportConfig({ selectedExporterEndpoint }: ExportConfigProps) {
	const dispatch = useAppDispatch();
	const exporter = useAppSelector((state) =>
		selectExporterByEndpoint(state, selectedExporterEndpoint),
	);

	const handleValueChange = (propertyKey: string, value: unknown) => {
		dispatch(
			updatePropertyValue({
				exporterEndpoint: selectedExporterEndpoint,
				propertyKey,
				value,
			}),
		);
	};

	const renderDocsLink = (docsUrl?: string, iconOnly = false) => {
		if (!docsUrl) {
			return null;
		}

		return (
			<a
				href={docsUrl}
				target="_blank"
				rel="noreferrer"
				className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
				title="Learn more"
			>
				{!iconOnly && <span>Learn more</span>}
				<ExternalLink className="h-3.5 w-3.5" />
			</a>
		);
	};

	const renderFieldHeader = (propertyKey: string) => {
		if (!exporter) {
			return null;
		}

		const property = exporter.properties[propertyKey];

		return (
			<div className="flex items-center gap-2">
				<FormLabel
					htmlFor={propertyKey}
					showRequired={property.required}
					className="mb-1"
				>
					{property.title || propertyKey}
				</FormLabel>
				{renderDocsLink(property.docsUrl, true)}
			</div>
		);
	};

	const renderField = (propertyKey: string) => {
		if (!exporter) {
			return null;
		}

		const property = exporter.properties[propertyKey];
		if (!property) {
			return null;
		}

		if (property.type === "boolean") {
			return (
				<div
					key={propertyKey}
					className="flex items-center justify-between gap-3"
					title={property.description}
				>
					<div className="flex items-center space-x-2">
						<Checkbox
							id={propertyKey}
							checked={
								exporter.propertyValues[propertyKey] === true ||
								exporter.propertyValues[propertyKey] === "true"
							}
							onCheckedChange={(checked) =>
								handleValueChange(propertyKey, checked)
							}
						/>
						<FormLabel htmlFor={propertyKey} showRequired={property.required}>
							<span className="cursor-pointer">
								{property.title || propertyKey}
							</span>
						</FormLabel>
					</div>
					{renderDocsLink(property.docsUrl, true)}
				</div>
			);
		}

		if (property.type === "contentWrappable") {
			const fileExtension = property.format || "txt";
			const fileName = `${propertyKey}.${fileExtension}`;
			const fieldTitle = property.title || propertyKey;

			return (
				<CollapsibleSection
					key={propertyKey}
					title={fieldTitle}
					defaultCollapsed={true}
					className="space-y-2"
				>
					{renderDocsLink(property.docsUrl)}
					<div className="h-48 border rounded-md overflow-hidden">
						<TextEditor
							language={property.format || "plaintext"}
							value={String(exporter.propertyValues[propertyKey] || "")}
							onChange={(value) => handleValueChange(propertyKey, value)}
							fullscreenTitle={fieldTitle}
							fileName={fileName}
						/>
					</div>
				</CollapsibleSection>
			);
		}

		if (property.type === "string") {
			return (
				<div key={propertyKey} className="space-y-2">
					{renderFieldHeader(propertyKey)}
					<Input
						id={propertyKey}
						value={String(exporter.propertyValues[propertyKey] || "")}
						onChange={(e) => handleValueChange(propertyKey, e.target.value)}
						placeholder={property.description}
					/>
				</div>
			);
		}

		if (property.type === "integer" || property.type === "number") {
			return (
				<div key={propertyKey} className="space-y-2">
					{renderFieldHeader(propertyKey)}
					<Input
						id={propertyKey}
						type="number"
						value={String(exporter.propertyValues[propertyKey] ?? "")}
						onChange={(e) => {
							// Store cleared numeric inputs as null so the form state represents "no value"
							// instead of NaN; exportSaga already omits null fields from API requests.
							if (e.target.value.trim() === "") {
								handleValueChange(propertyKey, null);
								return;
							}

							const numValue =
								property.type === "integer"
									? Number.parseInt(e.target.value, 10)
									: Number.parseFloat(e.target.value);
							handleValueChange(propertyKey, numValue);
						}}
						placeholder={property.description}
					/>
				</div>
			);
		}

		return null;
	};

	const renderContent = () => {
		if (!exporter) {
			return (
				<p className="text-muted-foreground italic text-sm">
					No configuration available
				</p>
			);
		}

		const propertyKeys = Object.keys(exporter.properties);

		if (propertyKeys.length === 0) {
			return (
				<p className="text-muted-foreground italic text-sm">No configuration</p>
			);
		}

		const booleanKeys: string[] = [];
		const stringKeys: string[] = [];
		const numberKeys: string[] = [];
		const contentWrappableKeys: string[] = [];

		for (const key of propertyKeys) {
			const property = exporter.properties[key];
			if (property.type === "boolean") {
				booleanKeys.push(key);
			} else if (property.type === "contentWrappable") {
				contentWrappableKeys.push(key);
			} else if (property.type === "string") {
				stringKeys.push(key);
			} else if (property.type === "integer" || property.type === "number") {
				numberKeys.push(key);
			}
		}

		const getSortedKeys = (required: boolean) => {
			const filterByRequired = (keys: string[]) =>
				keys.filter((key) => exporter.properties[key].required === required);

			return [
				...filterByRequired(contentWrappableKeys),
				...filterByRequired(stringKeys),
				...filterByRequired(numberKeys),
				...filterByRequired(booleanKeys),
			];
		};

		const requiredKeys = getSortedKeys(true);
		const optionalKeys = getSortedKeys(false);

		return (
			<div className="space-y-4 py-3">
				{requiredKeys.length > 0 && (
					<div className="space-y-4 px-4">
						{requiredKeys.map((key) => renderField(key))}
					</div>
				)}

				{optionalKeys.length > 0 && (
					<CollapsibleSection
						title="Export configuration"
						defaultCollapsed={true}
					>
						<div className="space-y-4 py-3">
							{optionalKeys.map((key) => renderField(key))}
						</div>
					</CollapsibleSection>
				)}
			</div>
		);
	};

	return renderContent();
}
