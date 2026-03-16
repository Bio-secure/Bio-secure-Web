FROM node:20

# Set work directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy frontend code
COPY . .

# Expose Vue dev server port
EXPOSE 5173

CMD ["npm", "run", "dev"]
