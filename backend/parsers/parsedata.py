import xml.etree.ElementTree as ET
import pandas as pd
import os

# Parse raw FAERS XML files into a CSV-friendly dataframe. This script
# is optimized for memory by using `iterparse` and clearing elements
# after processing. It is intended for offline preprocessing and may
# need adaptation for large-scale production pipelines.
xml_folder = os.path.join("faers_xml_2025Q4", "XML")

data = []

for file in os.listdir(xml_folder):

    if not file.endswith(".xml"):
        continue

    path = os.path.join(xml_folder, file)
    print("Processing:", file)

    try:
        # Use iterparse for memory efficiency, and handle potential XML errors
        context = ET.iterparse(path, events=("end",))

        for event, elem in context:
            # The tag might be prefixed with a namespace, e.g., {urn:hl7-org:v3}safetyreport
            # We check if the tag name ends with 'safetyreport' to be namespace-agnostic.
            if elem.tag.endswith("safetyreport"):

                # Extract namespace from the tag to use for finding children
                namespace = ''
                if '}' in elem.tag:
                    namespace = elem.tag.split('}')[0] + '}' # e.g., '{urn:hl7-org:v3}'

                # Helper to find elements with a namespace
                def find_ns(parent, path):
                    return parent.find(f"{namespace}{path}")

                def findall_ns(parent, path):
                    return parent.findall(f"{namespace}{path}")

                def findtext_ns(parent, path):
                    el = find_ns(parent, path)
                    return el.text if el is not None else None

                report_id = findtext_ns(elem, "safetyreportid")
                patient = find_ns(elem, "patient")

                if patient is None:
                    elem.clear()
                    continue

                age = findtext_ns(patient, "patientonsetage")
                gender = findtext_ns(patient, "patientsex")

                drugs = findall_ns(patient, "drug")
                reactions = findall_ns(patient, "reaction")

                for drug in drugs:
                    drug_name = findtext_ns(drug, "medicinalproduct")
                    indication = findtext_ns(drug, "drugindication")

                    for reaction in reactions:
                        reaction_name = findtext_ns(reaction, "reactionmeddrapt")

                        data.append({
                            "report_id": report_id, "drug_name": drug_name,
                            "disease": indication, "reaction": reaction_name,
                            "age": age, "gender": gender
                        })
                elem.clear()

    except ET.ParseError as e:
        print(f"  - XML Parse Error in {file}: {e}")

print("Parsing complete")

df = pd.DataFrame(data)

# Only remove rows missing essential values
df = df.dropna(subset=["drug_name", "reaction"])

df["drug_name"] = df["drug_name"].str.lower()
df["disease"] = df["disease"].str.lower()
df["reaction"] = df["reaction"].str.lower()

print(df.head())
print("Total records:", len(df))

df.to_csv("faers_parsed_dataset.csv", index=False)

print("Dataset saved successfully")