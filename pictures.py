from docx import Document
import os


def main():
    print("Запуск pictures.py")

if __name__ == "__main__":
    main()# Откройте документ DOCX
doc_path = 'data.docx'  # замените на путь к вашему файлу
doc = Document(doc_path)

# Создаем папку для сохранения изображений
output_dir = 'pictures'
os.makedirs(output_dir, exist_ok=True)

# Инициализация счетчика для названий изображений
image_counter = 1

# Перебор всех элементов в документе
for paragraph in doc.paragraphs:
    # Проверка на наличие изображений в параграфах
    for run in paragraph.runs:
        if run._element.xpath('.//a:blip'):
            # Извлечение изображения
            blip = run._element.xpath('.//a:blip')[0]
            image_id = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            image_part = doc.part.related_parts[image_id]

            # Формирование названия файла изображения
            image_filename = f"Рисунок {image_counter}.png"  # Название файла изображения с подписями

            # Сохранение изображения
            with open(os.path.join(output_dir, image_filename), 'wb') as img_file:
                img_file.write(image_part.blob)

            print(f'Изображение: {image_filename} сохранено.')
            image_counter += 1

# Вывод завершения
print("Изображения извлечены и сохранены с подписями.")
