FROM node:20-alpine AS base

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .

RUN npm run build

ENV HOSTNAME=0.0.0.0
EXPOSE 3000
CMD ["sh", "-c", "npm start -- -H 0.0.0.0 -p ${PORT:-3000}"]
