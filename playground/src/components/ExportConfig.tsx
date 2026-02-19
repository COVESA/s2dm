import { TextEditor } from "@/components/TextEditor";
import { Checkbox } from "@/components/ui/checkbox";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { FormLabel } from "@/components/ui/form-label";
import { Input } from "@/components/ui/input";
import {
	selectExporterByName,
	updatePropertyValue,
} from "@/store/capabilities/capabilitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type ExportConfigProps = {
	selectedExporter: string;
};

export function ExportConfig({ selectedExporter }: ExportConfigProps) {
	const dispatch = useAppDispatch();
	const exporter = useAppSelector((state) =>
		selectExporterByName(state, selectedExporter),
	);

	const handleValueChange = (propertyKey: string, value: unknown) => {
		dispatch(
			updatePropertyValue({
				exporterName: selectedExporter,
				propertyKey,
				value,
			}),
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
					className="flex items-center space-x-2"
					title={property.description}
				>
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
			);
		}

		if (property.type === "contentWrappable") {
			const fileExtension = property.format || "txt";
			const fileName = `${propertyKey}.${fileExtension}`;

			return (
				<div key={propertyKey} className="space-y-2">
					<FormLabel htmlFor={propertyKey} showRequired={property.required}>
						{property.title || propertyKey}
					</FormLabel>
					<div className="h-48 border rounded-md overflow-hidden">
						<TextEditor
							language={property.format || "plaintext"}
							value={String(exporter.propertyValues[propertyKey] || "")}
							onChange={(value) => handleValueChange(propertyKey, value)}
							fullscreenTitle={property.title || propertyKey}
							fileName={fileName}
						/>
					</div>
				</div>
			);
		}

		if (property.type === "string") {
			return (
				<div key={propertyKey} className="space-y-2">
					<FormLabel htmlFor={propertyKey} showRequired={property.required}>
						{property.title || propertyKey}
					</FormLabel>
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
					<FormLabel htmlFor={propertyKey} showRequired={property.required}>
						{property.title || propertyKey}
					</FormLabel>
					<Input
						id={propertyKey}
						type="number"
						value={String(exporter.propertyValues[propertyKey] ?? "")}
						onChange={(e) => {
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

		const sortByRequired = (keys: string[]) => {
			const required = keys.filter((key) => exporter.properties[key].required);
			const optional = keys.filter((key) => !exporter.properties[key].required);
			return [...required, ...optional];
		};

		const sortedContentWrappableKeys = sortByRequired(contentWrappableKeys);
		const sortedBooleanKeys = sortByRequired(booleanKeys);
		const sortedStringKeys = sortByRequired(stringKeys);
		const sortedNumberKeys = sortByRequired(numberKeys);

		const allSortedKeys = [
			...sortedContentWrappableKeys,
			...sortedStringKeys,
			...sortedNumberKeys,
			...sortedBooleanKeys,
		];

		return (
			<div className="space-y-4 py-3">
				{allSortedKeys.map((key) => renderField(key))}
			</div>
		);
	};

	return (
		<CollapsibleSection title="Export configuration">
			{renderContent()}
		</CollapsibleSection>
	);
}
